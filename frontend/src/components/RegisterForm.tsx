import { useState, useEffect, type FormEvent } from "react";
import { useAuth } from "../contexts/AuthContext";
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
  SUCCESS,
  SUCCESS_BG20,
} from "../theme";

interface RegisterFormProps {
  onToggle: () => void;
}

export default function RegisterForm({ onToggle }: RegisterFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const { register } = useAuth();
  const { isMobile } = useMediaQuery();

  useEffect(() => {
    if (!success) return;
    const t = setTimeout(() => onToggle(), 1500);
    return () => clearTimeout(t);
  }, [success, onToggle]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(false);

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    try {
      const ok = await register(email, password, name);
      if (ok) {
        setSuccess(true);
      } else {
        setError("Registration failed. Email may already be in use.");
      }
    } catch {
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
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
        Create Account
      </h2>

      {success && (
        <div
          style={{
            backgroundColor: SUCCESS_BG20,
            border: `1px solid ${SUCCESS}`,
            borderRadius: `${RADIUS.md}px`,
            color: SUCCESS,
            fontFamily: TYPO.small.fontFamily,
            fontSize: `${TYPO.small.fontSize}px`,
            padding: "12px",
            marginBottom: "16px",
            textAlign: "center",
          }}
        >
          Account created successfully! Redirecting to sign in...
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
            Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
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
          <span
            style={{
              color: TEXT_MUTED,
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
            }}
          >
            Must be at least 8 characters
          </span>
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
          disabled={loading || success}
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
            opacity: loading || success ? 0.7 : 1,
            marginTop: "4px",
          }}
          onMouseEnter={(e) => {
            if (!loading && !success) (e.target as HTMLElement).style.opacity = "0.9";
          }}
          onMouseLeave={(e) => {
            if (!loading && !success) (e.target as HTMLElement).style.opacity = "1";
          }}
        >
          {loading ? "Creating account..." : "Create Account"}
        </button>
      </form>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          marginTop: "20px",
          paddingTop: "20px",
          borderTop: `1px solid ${BORDER}`,
        }}
      >
        <span
          style={{
            color: TEXT_SECONDARY,
            fontFamily: TYPO.small.fontFamily,
            fontSize: `${TYPO.small.fontSize}px`,
          }}
        >
          Already have an account?
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
          Sign in
        </button>
      </div>
    </div>
  );
}
