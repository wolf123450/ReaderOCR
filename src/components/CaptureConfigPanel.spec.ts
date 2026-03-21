import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import CaptureConfigPanel from "@/components/CaptureConfigPanel.vue";
import { useUiStore } from "@/stores/ui";
import { useCaptureStore } from "@/stores/capture";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn() }));
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: vi.fn() }));

function makeWindow() {
  return { handle: 1, title: "Kindle for PC", x: 0, y: 0, width: 1200, height: 800, process_name: "kindle" };
}
function makeRegion() {
  return { x: 100, y: 100, width: 800, height: 600 };
}

describe("CaptureConfigPanel — Step 45", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("5. expanded state rendered when captureConfigCollapsed = false", () => {
    const wrapper = mount(CaptureConfigPanel, { slots: { default: "<p>picker content</p>" } });
    expect(wrapper.find(".expanded-content").exists()).toBe(true);
    expect(wrapper.find(".summary-bar").exists()).toBe(false);
    expect(wrapper.text()).toContain("picker content");
  });

  it("6. collapsed summary bar shown when captureConfigCollapsed = true (with window + region)", () => {
    const capture = useCaptureStore();
    capture.selectedWindow = makeWindow();
    capture.region = makeRegion();
    const ui = useUiStore();
    ui.setCaptureConfigCollapsed(true);

    const wrapper = mount(CaptureConfigPanel, { slots: { default: "<p>picker content</p>" } });
    expect(wrapper.find(".summary-bar").exists()).toBe(true);
    expect(wrapper.find(".expanded-content").exists()).toBe(false);
  });

  it("7. summary bar shows correct window title and region dimensions", () => {
    const capture = useCaptureStore();
    capture.selectedWindow = makeWindow();
    capture.region = makeRegion();
    const ui = useUiStore();
    ui.setCaptureConfigCollapsed(true);

    const wrapper = mount(CaptureConfigPanel);
    const barText = wrapper.find(".summary-bar").text();
    expect(barText).toContain("Kindle for PC");
    expect(barText).toContain("800×600 px");
  });

  it("8a. clicking Edit when not capturing expands (sets captureConfigCollapsed=false)", async () => {
    const capture = useCaptureStore();
    capture.selectedWindow = makeWindow();
    capture.region = makeRegion();
    const ui = useUiStore();
    ui.setCaptureConfigCollapsed(true);

    const wrapper = mount(CaptureConfigPanel, { slots: { default: "<p>content</p>" } });
    await wrapper.find(".edit-btn").trigger("click");
    expect(ui.captureConfigCollapsed).toBe(false);
    expect(wrapper.emitted("pause-and-expand")).toBeUndefined();
  });

  it("8b. clicking Edit while capturing emits pause-and-expand", async () => {
    const capture = useCaptureStore();
    capture.selectedWindow = makeWindow();
    capture.region = makeRegion();
    capture.transitionTo("capturing");
    const ui = useUiStore();
    ui.setCaptureConfigCollapsed(true);

    const wrapper = mount(CaptureConfigPanel, { slots: { default: "<p>content</p>" } });
    await wrapper.find(".edit-btn").trigger("click");
    expect(wrapper.emitted("pause-and-expand")).toBeTruthy();
    // collapsed state not changed yet (caller handles it)
    expect(ui.captureConfigCollapsed).toBe(true);
  });

  it("9. Collapse button visible in expanded state; clicking it collapses", async () => {
    const capture = useCaptureStore();
    capture.selectedWindow = makeWindow();
    capture.region = makeRegion();

    const wrapper = mount(CaptureConfigPanel, { slots: { default: "<p>content</p>" } });
    const collapseBtn = wrapper.find(".collapse-btn");
    expect(collapseBtn.exists()).toBe(true);
    expect((collapseBtn.element as HTMLButtonElement).disabled).toBe(false);

    await collapseBtn.trigger("click");
    const ui = useUiStore();
    expect(ui.captureConfigCollapsed).toBe(true);
  });

  it("10. Collapse button disabled with tooltip when no window selected", () => {
    const wrapper = mount(CaptureConfigPanel);
    const collapseBtn = wrapper.find(".collapse-btn");
    expect((collapseBtn.element as HTMLButtonElement).disabled).toBe(true);
    expect(collapseBtn.attributes("title")).toBe("Select a window and region first");
  });
});
