import { SignIn, useUser } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { PRIMARY, PAGE_BG } from "../theme";

export default function AuthPage() {
  const { isSignedIn } = useUser();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();

  // Redirect already-logged-in users away from auth page
  useEffect(() => {
    if (isSignedIn) {
      navigate("/", { replace: true });
    }
  }, [isSignedIn, navigate]);

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "80vh",
        padding: isMobile ? "20px" : "40px",
      }}
    >
      <SignIn
        appearance={{
          variables: {
            colorPrimary: PRIMARY,
            colorBackground: PAGE_BG,
            colorText: "#f1f5f9",
            colorInputBackground: "#1e293b",
            colorInputText: "#f1f5f9",
            borderRadius: "8px",
          },
          elements: {
            card: {
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
            },
            headerTitle: {
              color: "#f1f5f9",
            },
            headerSubtitle: {
              color: "#94a3b8",
            },
            socialButtonsBlockButton: {
              backgroundColor: "#0f172a",
              border: "1px solid #334155",
              color: "#f1f5f9",
            },
            formFieldLabel: {
              color: "#94a3b8",
            },
            formFieldInput: {
              backgroundColor: "#0f172a",
              border: "1px solid #334155",
              color: "#f1f5f9",
            },
            footerActionLink: {
              color: PRIMARY,
            },
          },
        }}
      />
    </div>
  );
}
