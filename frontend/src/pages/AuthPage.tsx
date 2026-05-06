import { SignIn, useUser, useAuth } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useMediaQuery } from "../hooks/useMediaQuery";
import * as api from "../services/api";
import {
  PAGE_BG,
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
} from "../theme";

export default function AuthPage() {
  const { isSignedIn, user } = useUser();
  const { getToken, isLoaded } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();
  const [syncing, setSyncing] = useState(false);

  // Handle auth completion and user sync
  useEffect(() => {
    if (!isLoaded || !isSignedIn || !user) return;

    // Already signed in - sync with backend and redirect
    const syncAndRedirect = async () => {
      setSyncing(true);
      try {
        const token = await getToken();
        if (token) {
          localStorage.setItem("auth_token", token);
          // Sync user with backend
          await api.getMe();
        }
        navigate("/", { replace: true });
      } catch (err) {
        console.error("Failed to sync after sign in:", err);
        // Still redirect even if sync fails - AuthContext will retry
        navigate("/", { replace: true });
      } finally {
        setSyncing(false);
      }
    };

    syncAndRedirect();
  }, [isSignedIn, isLoaded, user, getToken, navigate]);

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "80vh",
        padding: isMobile ? "16px" : "40px",
        backgroundColor: PAGE_BG,
      }}
    >
      {syncing ? (
        <div style={{ color: TEXT_PRIMARY, textAlign: "center" }}>
          <div style={{ fontSize: "24px", marginBottom: "16px" }}>✓</div>
          <div>Signed in! Redirecting...</div>
        </div>
      ) : (
        <SignIn
          routing="hash"
          signUpUrl="/sign-up"
        appearance={{
          variables: {
            colorPrimary: PRIMARY,
            colorBackground: CARD_BG,
            colorText: TEXT_PRIMARY,
            colorInputBackground: INPUT_BG,
            colorInputText: TEXT_PRIMARY,
            colorTextSecondary: TEXT_SECONDARY,
            colorTextOnPrimaryBackground: PAGE_BG,
            fontFamily: TYPO.body.fontFamily,
            fontFamilyButtons: TYPO.body.fontFamily,
            fontSize: `${TYPO.body.fontSize}px`,
            borderRadius: `${RADIUS.md}px`,
            spacingUnit: "16px",
          },
          elements: {
            rootBox: {
              width: "100%",
              maxWidth: "400px",
            },
            card: {
              backgroundColor: CARD_BG,
              border: `1px solid ${BORDER}`,
              borderRadius: `${RADIUS.md}px`,
              boxShadow: "none",
            },
            header: {
              padding: "24px",
              borderBottom: `1px solid ${BORDER}`,
            },
            headerTitle: {
              color: TEXT_PRIMARY,
              fontFamily: TYPO.h3.fontFamily,
              fontSize: `${TYPO.h3.fontSize}px`,
              fontWeight: TYPO.h3.fontWeight,
              lineHeight: TYPO.h3.lineHeight,
            },
            headerSubtitle: {
              color: TEXT_SECONDARY,
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
              lineHeight: TYPO.small.lineHeight,
            },
            socialButtonsBlockButton: {
              backgroundColor: PAGE_BG,
              border: `1px solid ${BORDER}`,
              borderRadius: `${RADIUS.md}px`,
              color: TEXT_PRIMARY,
              fontFamily: TYPO.body.fontFamily,
              fontSize: `${TYPO.body.fontSize}px`,
              height: "44px",
              transition: "border-color 0.15s ease",
            },
            "socialButtonsBlockButton:hover": {
              borderColor: BORDER_LIGHT,
            },
            socialButtonsBlockButtonText: {
              color: TEXT_PRIMARY,
              fontFamily: TYPO.body.fontFamily,
            },
            dividerLine: {
              backgroundColor: BORDER,
            },
            dividerText: {
              color: TEXT_MUTED,
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
            },
            formFieldLabel: {
              color: TEXT_SECONDARY,
              fontFamily: TYPO.label.fontFamily,
              fontSize: `${TYPO.label.fontSize}px`,
              fontWeight: TYPO.label.fontWeight,
              textTransform: TYPO.label.textTransform,
              letterSpacing: TYPO.label.letterSpacing,
              lineHeight: TYPO.label.lineHeight,
            },
            formFieldInput: {
              backgroundColor: INPUT_BG,
              border: `1px solid ${BORDER}`,
              borderRadius: `${RADIUS.md}px`,
              color: TEXT_PRIMARY,
              fontFamily: TYPO.body.fontFamily,
              fontSize: `${TYPO.body.fontSize}px`,
              height: "44px",
              transition: "border-color 0.15s ease",
            },
            "formFieldInput:focus": {
              borderColor: PRIMARY,
              outline: "none",
            },
            formButtonPrimary: {
              backgroundColor: PRIMARY,
              border: `1px solid ${PRIMARY}`,
              borderRadius: `${RADIUS.md}px`,
              color: PAGE_BG,
              fontFamily: TYPO.body.fontFamily,
              fontSize: `${TYPO.body.fontSize}px`,
              fontWeight: 500,
              height: "44px",
              transition: "opacity 0.15s ease",
            },
            "formButtonPrimary:hover": {
              opacity: "0.9",
            },
            formButtonSecondary: {
              backgroundColor: "transparent",
              border: `1px solid ${BORDER}`,
              borderRadius: `${RADIUS.md}px`,
              color: TEXT_PRIMARY,
              fontFamily: TYPO.body.fontFamily,
              fontSize: `${TYPO.body.fontSize}px`,
            },
            "formButtonSecondary:hover": {
              backgroundColor: INPUT_BG,
            },
            footer: {
              padding: "24px",
              borderTop: `1px solid ${BORDER}`,
            },
            footerActionText: {
              color: TEXT_SECONDARY,
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
            },
            footerActionLink: {
              color: PRIMARY,
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
              fontWeight: 500,
              textDecoration: "none",
            },
            "footerActionLink:hover": {
              textDecoration: "underline",
            },
            identityPreview: {
              backgroundColor: INPUT_BG,
              border: `1px solid ${BORDER}`,
              borderRadius: `${RADIUS.md}px`,
            },
            identityPreviewText: {
              color: TEXT_PRIMARY,
              fontFamily: TYPO.body.fontFamily,
            },
            formFieldInfoText: {
              color: TEXT_MUTED,
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
            },
            formFieldErrorText: {
              color: "#ef4444",
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
            },
            alert: {
              backgroundColor: "#ef444420",
              border: "1px solid #ef4444",
              borderRadius: `${RADIUS.md}px`,
            },
            alertText: {
              color: "#ef4444",
              fontFamily: TYPO.small.fontFamily,
              fontSize: `${TYPO.small.fontSize}px`,
            },
            spinner: {
              borderTopColor: PRIMARY,
            },
            logoImage: {
              filter: "grayscale(100%)",
            },
          },
          layout: {
            socialButtonsPlacement: "top",
          },
        }}
      />
      )}
    </div>
  );
}
