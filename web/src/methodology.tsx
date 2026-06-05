import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource-variable/fraunces";
import "@fontsource-variable/inter";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "./tokens/colors_and_type.css";
import "./styles/app.css";
import { MethodologyPage } from "./pages/MethodologyPage";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MethodologyPage />
  </React.StrictMode>,
);
