import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { useMediaQuery } from "../hooks/useMediaQuery";
import LoginForm from "../components/LoginForm";
import RegisterForm from "../components/RegisterForm";
import ForgotPasswordForm from "../components/ForgotPasswordForm";
import ResetPasswordForm from "../components/ResetPasswordForm";
import {
  PAGE_BG,
} from "../theme";

type AuthMode = "login" | "register" | "forgot" | "reset";

export default function AuthPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading } = useAuth();
  const { isMobile } = useMediaQuery();

  const getInitialMode = (): AuthMode => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("token")) return "reset";
    return "login";
  };

  const [mode, setMode] = useState<AuthMode>(getInitialMode);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate("/", { replace: true });
    }
  }, [isLoading, isAuthenticated, navigate]);

  if (isLoading) {
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
        <div style={{ color: "#f1f5f9", textAlign: "center" }}>Loading...</div>
      </div>
    );
  }

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
      {mode === "login" && (
        <LoginForm
          onToggle={() => setMode("register")}
          onForgotPassword={() => setMode("forgot")}
        />
      )}
      {mode === "register" && (
        <RegisterForm
          onToggle={() => setMode("login")}
        />
      )}
      {mode === "forgot" && (
        <ForgotPasswordForm
          onBack={() => setMode("login")}
        />
      )}
      {mode === "reset" && (
        <ResetPasswordForm
          onBack={() => setMode("login")}
        />
      )}
    </div>
  );
}
