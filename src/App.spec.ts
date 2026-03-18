import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import App from "@/App.vue";

// Mock Tauri invoke since CaptureView uses it
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn().mockResolvedValue([]),
}));

// Mock Tauri event listener
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(() => {}),
}));

// Mock Tauri dialog plugin
vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: vi.fn().mockResolvedValue(null),
}));

describe("App", () => {
  it("mounts successfully", () => {
    const wrapper = mount(App, {
      global: { plugins: [createPinia()] },
    });
    expect(wrapper.exists()).toBe(true);
  });

  it("displays KindleOCR heading", () => {
    const wrapper = mount(App, {
      global: { plugins: [createPinia()] },
    });
    expect(wrapper.text()).toContain("KindleOCR");
  });

  it("renders CaptureView", () => {
    const wrapper = mount(App, {
      global: { plugins: [createPinia()] },
    });
    expect(wrapper.find(".capture-view").exists()).toBe(true);
  });
});
