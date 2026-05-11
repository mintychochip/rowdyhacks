import { useState, type FormEvent } from "react";
import { useMediaQuery } from "../hooks/useMediaQuery";
import {
  CARD_BG,
  INPUT_BG,
  PRIMARY,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  BORDER,
  RADIUS,
  TYPO,
  ERROR,
  SUCCESS,
  SUCCESS_BG20,
} from "../theme";

interface ResetPasswordFormProps {
  onBack: () => void;
}

function getTokenFromUrl(): string {
  const params = new URLSearchParams(window.location.search);
  return params.get("token") || "";
}

export default function ResetPasswordForm({ onBack }: ResetPasswordFormProps) {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const { isMobile } = useMediaQuery();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    const token = getTokenFromUrl();
    if (!token) {
      setError("Invalid or missing reset token");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: newPassword }),
      });
      const data = await res.json();
      if (res.ok) {
        setSuccess(true);
      } else {
        setError(data.detail || "Failed to reset password");
      }
    } catch {
      setError("Network error. Please try again.");
    }
    setLoading(false);
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
        Reset Password
      </h2>

      {success ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div
            style={{
              backgroundColor: SUCCESS_BG20,
              border: `1px solid ${SUCCESS}`,
              borderRadius: `${RADIUS.md}px`,
              color: SUCCESS,
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
              padding: "12px",
              textAlign: "center",
            }}
          >
            Your password has been reset successfully.
          </div>
          <button
            type="button"
            onClick={onBack}
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
            }}
            onMouseEnter={(e) => {
              (e.target as HTMLElement).style.opacity = "0.9";
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.opacity = "1";
            }}
          >
            Back to sign in
          </button>
        </div>
      ) : (
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
              New Password
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
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
              Confirm Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
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
            {loading ? "Resetting..." : "Reset Password"}
          </button>
        </form>
      )}

      {!success && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginTop: "20px",
            paddingTop: "20px",
            borderTop: `1px solid ${BORDER}`,
          }}
        >
          <button
            type="button"
            onClick={onBack}
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
            Back to sign in
          </button>
        </div>
      )}
    </div>
  );
}
