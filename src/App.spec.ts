import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import App from "@/App.vue";

describe("App", () => {
  it("mounts successfully", () => {
    const wrapper = mount(App);
    expect(wrapper.exists()).toBe(true);
  });

  it("displays KindleOCR heading", () => {
    const wrapper = mount(App);
    expect(wrapper.text()).toContain("KindleOCR");
  });
});
