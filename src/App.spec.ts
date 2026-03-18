import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import App from "@/App.vue";

// Mock Tauri invoke since CaptureView uses it
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn().mockResolvedValue([]),
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
