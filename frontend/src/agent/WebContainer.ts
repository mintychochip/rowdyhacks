// WebContainer sandbox manager — provides isolated Node.js runtime in browser.
// Only works in Chrome/Edge (requires SharedArrayBuffer).

import { WebContainer, type FileSystemTree } from '@webcontainer/api';

type SandboxStatus = 'idle' | 'booting' | 'ready' | 'error' | 'expired';

export class Sandbox {
  private instance: WebContainer | null = null;
  private bootPromise: Promise<WebContainer> | null = null;
  status: SandboxStatus = 'idle';
  onStatusChange?: (status: SandboxStatus) => void;

  private setStatus(s: SandboxStatus) {
    this.status = s;
    this.onStatusChange?.(s);
  }

  async ensure(): Promise<WebContainer> {
    if (this.instance) return this.instance;
    if (this.bootPromise) return this.bootPromise;

    this.setStatus('booting');
    this.bootPromise = WebContainer.boot()
      .then(wc => {
        this.instance = wc;
        this.setStatus('ready');
        wc.mount({
          'package.json': { file: { contents: '{"name":"hack-project","private":true}' } },
          'README.md': { file: { contents: '# OpenHack Project' } },
        });
        wc.on('server-ready', (_port: number, url: string) => {
          console.log(`[Sandbox] Server ready: ${url}`);
        });
        return wc;
      })
      .catch(err => {
        this.bootPromise = null;
        this.setStatus('error');
        throw err;
      });

    return this.bootPromise;
  }

  async readFile(path: string): Promise<string> {
    const wc = await this.ensure();
    const content = await wc.fs.readFile(path, 'utf-8');
    return content as string;
  }

  async writeFile(path: string, content: string): Promise<void> {
    const wc = await this.ensure();
    await wc.fs.writeFile(path, content);
  }

  async editFile(path: string, oldStr: string, newStr: string): Promise<void> {
    const content = await this.readFile(path);
    if (!content.includes(oldStr)) {
      throw new Error(`Could not find string to replace in ${path}`);
    }
    const updated = content.replace(oldStr, newStr);
    await this.writeFile(path, updated);
  }

  async bash(command: string): Promise<{ stdout: string; stderr: string; exitCode: number }> {
    const wc = await this.ensure();
    const process = await wc.spawn('bash', ['-c', command]);

    let stdout = '';
    let stderr = '';

    process.output.pipeTo(
      new WritableStream({
        write(data) {
          stdout += data;
        },
      })
    );

    const exitCode = await process.exit;
    return { stdout, stderr, exitCode };
  }

  reset(): void {
    this.instance = null;
    this.bootPromise = null;
    this.setStatus('idle');
  }
}

export const sandbox = new Sandbox();
