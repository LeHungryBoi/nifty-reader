import { mount } from "svelte";
import { getCurrentWindow, LogicalSize } from "@tauri-apps/api/window";
import App from "./App.svelte";

async function resizeMainWindowToEightyPercentHeight() {
  if (!("__TAURI_INTERNALS__" in window)) {
    return;
  }

  try {
    const appWindow = getCurrentWindow();
    const monitor = await appWindow.currentMonitor();

    if (!monitor) {
      return;
    }

    const currentSize = await appWindow.innerSize();
    const targetHeight = Math.max(600, Math.floor(monitor.size.height * 0.8));

    await appWindow.setSize(new LogicalSize(currentSize.width, targetHeight));
    await appWindow.center();
  } catch (error) {
    console.error("Unable to resize main window:", error);
  }
}

void resizeMainWindowToEightyPercentHeight();
mount(App, { target: document.getElementById("root")! });
