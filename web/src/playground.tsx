import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource-variable/fraunces";
import "@fontsource-variable/inter";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "./tokens/colors_and_type.css";
import "./styles/app.css";
import { PlaygroundPage } from "./pages/PlaygroundPage";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PlaygroundPage />
  </React.StrictMode>,
);
