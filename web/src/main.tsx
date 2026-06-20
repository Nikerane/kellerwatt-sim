import "@fontsource-variable/fraunces";
import "@fontsource-variable/inter";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "./tokens/colors_and_type.css";
import "./styles/app.css";
import { App } from "./App";
import { withGate } from "./gate";

withGate(<App />);
