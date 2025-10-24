import React from "react";
import { createRoot } from "react-dom/client";
import App from "./app";

import "./index.css";

const el = document.getElementById("root");
if (el) createRoot(el).render(<App />);