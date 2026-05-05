import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY, CYAN, CARD_BG, BORDER } from '../theme';

interface MarkdownRendererProps {
  content: string;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div style={{
      color: TEXT_PRIMARY,
      lineHeight: 1.7,
      fontSize: 15,
    }}>
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 style={{
              fontSize: 28,
              fontWeight: 700,
              margin: '24px 0 16px',
              color: TEXT_PRIMARY,
              borderBottom: `1px solid ${BORDER}`,
              paddingBottom: 8,
            }}>{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 style={{
              fontSize: 22,
              fontWeight: 600,
              margin: '20px 0 12px',
              color: PRIMARY,
            }}>{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 style={{
              fontSize: 18,
              fontWeight: 600,
              margin: '16px 0 8px',
              color: CYAN,
            }}>{children}</h3>
          ),
          p: ({ children }) => (
            <p style={{ margin: '12px 0', color: TEXT_SECONDARY }}>{children}</p>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: PRIMARY,
                textDecoration: 'none',
                borderBottom: `1px solid ${PRIMARY}40`,
              }}
            >{children}</a>
          ),
          ul: ({ children }) => (
            <ul style={{ margin: '12px 0', paddingLeft: 24, color: TEXT_SECONDARY }}>{children}</ul>
          ),
          ol: ({ children }) => (
            <ol style={{ margin: '12px 0', paddingLeft: 24, color: TEXT_SECONDARY }}>{children}</ol>
          ),
          li: ({ children }) => (
            <li style={{ margin: '4px 0' }}>{children}</li>
          ),
          code: ({ children, className }) => {
            const match = /language-(\w+)/.exec(className || '');
            const isInline = !match && !className;

            if (isInline) {
              return (
                <code style={{
                  background: `${CARD_BG}`,
                  padding: '2px 6px',
                  borderRadius: 4,
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 13,
                  color: CYAN,
                }}>{children}</code>
              );
            }

            return (
              <SyntaxHighlighter
                style={vscDarkPlus}
                language={match ? match[1] : 'text'}
                PreTag="div"
                customStyle={{
                  borderRadius: 8,
                  margin: '16px 0',
                  fontSize: 13,
                }}
              >{String(children).replace(/\n$/, '')}</SyntaxHighlighter>
            );
          },
          blockquote: ({ children }) => (
            <blockquote style={{
              borderLeft: `3px solid ${PRIMARY}`,
              margin: '16px 0',
              padding: '8px 16px',
              background: `${CARD_BG}`,
              borderRadius: '0 8px 8px 0',
            }}>{children}</blockquote>
          ),
          table: ({ children }) => (
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              margin: '16px 0',
              fontSize: 14,
            }}>{children}</table>
          ),
          thead: ({ children }) => <thead style={{ background: CARD_BG }}>{children}</thead>,
          th: ({ children }) => (
            <th style={{
              padding: '10px 12px',
              textAlign: 'left',
              fontWeight: 600,
              color: TEXT_PRIMARY,
              borderBottom: `1px solid ${BORDER}`,
            }}>{children}</th>
          ),
          td: ({ children }) => (
            <td style={{
              padding: '8px 12px',
              color: TEXT_SECONDARY,
              borderBottom: `1px solid ${BORDER}`,
            }}>{children}</td>
          ),
          hr: () => (
            <hr style={{
              border: 'none',
              borderTop: `1px solid ${BORDER}`,
              margin: '24px 0',
            }} />
          ),
        }}
      >{content}</ReactMarkdown>
    </div>
  );
}
