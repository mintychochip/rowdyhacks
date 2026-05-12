import { useState, useEffect, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useMediaQuery } from "../hooks/useMediaQuery";
import {
  CARD_BG,
  INPUT_BG,
  PRIMARY,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  BORDER,
  BORDER_LIGHT,
  RADIUS,
  TYPO,
  ERROR,
} from "../theme";

interface OAuthProvider {
  name: string;
  display_name: string;
}

interface LoginFormProps {
  onToggle: () => void;
  onForgotPassword: () => void;
}

export default function LoginForm({ onToggle, onForgotPassword }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [providers, setProviders] = useState<OAuthProvider[]>([]);
  const [oauthLoading, setOAuthLoading] = useState<string | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();

  useEffect(() => {
    fetch("/api/auth/providers")
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) setProviders(data);
      })
      .catch(() => {
        setProviders([]);
      });
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const ok = await login(email, password);
      if (ok) {
        navigate("/");
      } else {
        setError("Invalid email or password");
      }
    } catch {
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleOAuth = async (provider: string) => {
    setOAuthLoading(provider);
    try {
      const res = await fetch(`/api/auth/oauth/${provider}/login`);
      if (!res.ok) throw new Error("Failed to initiate OAuth");
      const data = await res.json();
      if (data.authorization_url) {
        const url = new URL(data.authorization_url);
        window.location.href = url.href;
      }
    } catch {
      setError("Failed to initiate OAuth login. Please try again.");
    } finally {
      setOAuthLoading(null);
    }
  };

  return (
    <div
      style={{
        backgroundColor: CARD_BG,
        border: `1px solid ${BORDER}`,
        borderRadius: `${RADIUS.md}px`,
        width: "100%",
        maxWidth: "400px",
        padding: isMobile ? "24px 20px" : "32px",
      }}
    >
      <h2
        style={{
          color: TEXT_PRIMARY,
          fontFamily: TYPO.h3.fontFamily,
          fontSize: `${TYPO.h3.fontSize}px`,
          fontWeight: TYPO.h3.fontWeight,
          lineHeight: TYPO.h3.lineHeight,
          margin: "0 0 24px 0",
          textAlign: "center",
        }}
      >
        Sign In
      </h2>

      {providers.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "20px" }}>
          {providers.map((p) => (
            <button
              key={p.name}
              type="button"
              onClick={() => handleOAuth(p.name)}
              disabled={!!oauthLoading}
              style={{
                backgroundColor: "transparent",
                border: `1px solid ${BORDER}`,
                borderRadius: `${RADIUS.md}px`,
                color: TEXT_PRIMARY,
                fontFamily: TYPO.body.fontFamily,
                fontSize: `${TYPO.body.fontSize}px`,
                height: "44px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                transition: "border-color 0.15s ease, background-color 0.15s ease",
                opacity: oauthLoading === p.name ? 0.7 : 1,
              }}
              onMouseEnter={(e) => {
                (e.target as HTMLElement).style.borderColor = BORDER_LIGHT;
                (e.target as HTMLElement).style.backgroundColor = INPUT_BG;
              }}
              onMouseLeave={(e) => {
                (e.target as HTMLElement).style.borderColor = BORDER;
                (e.target as HTMLElement).style.backgroundColor = "transparent";
              }}
            >
              {oauthLoading === p.name ? "Redirecting..." : `Sign in with ${p.display_name}`}
            </button>
          ))}
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginTop: "4px" }}>
            <div style={{ flex: 1, height: "1px", backgroundColor: BORDER }} />
            <span
              style={{
                color: TEXT_MUTED,
                fontFamily: TYPO.small.fontFamily,
                fontSize: `${TYPO.small.fontSize}px`,
              }}
            >
              or
            </span>
            <div style={{ flex: 1, height: "1px", backgroundColor: BORDER }} />
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label
            style={{
              color: TEXT_SECONDARY,
              fontFamily: TYPO.label.fontFamily,
              fontSize: `${TYPO.label.fontSize}px`,
              fontWeight: TYPO.label.fontWeight,
              textTransform: TYPO.label.textTransform,
              letterSpacing: TYPO.label.letterSpacing,
              lineHeight: TYPO.label.lineHeight,
            }}
          >
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{
              backgroundColor: INPUT_BG,
              border: `1px solid ${BORDER}`,
              borderRadius: `${RADIUS.md}px`,
              color: TEXT_PRIMARY,
              fontFamily: TYPO.body.fontFamily,
              fontSize: `${TYPO.body.fontSize}px`,
              height: "44px",
              padding: "0 12px",
              outline: "none",
              transition: "border-color 0.15s ease",
            }}
            onFocus={(e) => {
              e.target.style.borderColor = PRIMARY;
            }}
            onBlur={(e) => {
              e.target.style.borderColor = BORDER;
            }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label
            style={{
              color: TEXT_SECONDARY,
              fontFamily: TYPO.label.fontFamily,
              fontSize: `${TYPO.label.fontSize}px`,
              fontWeight: TYPO.label.fontWeight,
              textTransform: TYPO.label.textTransform,
              letterSpacing: TYPO.label.letterSpacing,
              lineHeight: TYPO.label.lineHeight,
            }}
          >
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{
              backgroundColor: INPUT_BG,
              border: `1px solid ${BORDER}`,
              borderRadius: `${RADIUS.md}px`,
              color: TEXT_PRIMARY,
              fontFamily: TYPO.body.fontFamily,
              fontSize: `${TYPO.body.fontSize}px`,
              height: "44px",
              padding: "0 12px",
              outline: "none",
              transition: "border-color 0.15s ease",
            }}
            onFocus={(e) => {
              e.target.style.borderColor = PRIMARY;
            }}
            onBlur={(e) => {
              e.target.style.borderColor = BORDER;
            }}
          />
        </div>

        {error && (
          <div
            style={{
              color: ERROR,
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
              textAlign: "center",
            }}
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            backgroundColor: PRIMARY,
            border: `1px solid ${PRIMARY}`,
            borderRadius: `${RADIUS.md}px`,
            color: "#fff",
            fontFamily: TYPO.body.fontFamily,
            fontSize: `${TYPO.body.fontSize}px`,
            fontWeight: 500,
            height: "44px",
            cursor: "pointer",
            transition: "opacity 0.15s ease",
            opacity: loading ? 0.7 : 1,
            marginTop: "4px",
          }}
          onMouseEnter={(e) => {
            if (!loading) (e.target as HTMLElement).style.opacity = "0.9";
          }}
          onMouseLeave={(e) => {
            if (!loading) (e.target as HTMLElement).style.opacity = "1";
          }}
        >
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "12px",
          marginTop: "20px",
          paddingTop: "20px",
          borderTop: `1px solid ${BORDER}`,
        }}
      >
        <button
          type="button"
          onClick={onForgotPassword}
          style={{
            background: "none",
            border: "none",
            color: PRIMARY,
            fontFamily: TYPO.small.fontFamily,
            fontSize: `${TYPO.small.fontSize}px`,
            fontWeight: 500,
            cursor: "pointer",
            textDecoration: "none",
            padding: 0,
          }}
          onMouseEnter={(e) => {
            (e.target as HTMLElement).style.textDecoration = "underline";
          }}
          onMouseLeave={(e) => {
            (e.target as HTMLElement).style.textDecoration = "none";
          }}
        >
          Forgot password?
        </button>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span
            style={{
              color: TEXT_SECONDARY,
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
            }}
          >
            Don&apos;t have an account?
          </span>
          <button
            type="button"
            onClick={onToggle}
            style={{
              background: "none",
              border: "none",
              color: PRIMARY,
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
              fontWeight: 500,
              cursor: "pointer",
              textDecoration: "none",
              padding: 0,
            }}
            onMouseEnter={(e) => {
              (e.target as HTMLElement).style.textDecoration = "underline";
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.textDecoration = "none";
            }}
          >
            Create account
          </button>
        </div>
      </div>
    </div>
  );
}
