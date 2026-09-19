import type { Product } from "@/data/products";

export interface ComparisonRow {
  readonly label: string;
  readonly value: (product: Product) => string;
}

const yesNo = (value: boolean) => (value ? "Included" : "Not included");

export const comparisonRows = [
  { label: "Web UI", value: () => "Included" },
  { label: "Integrated display", value: (product) => yesNo(product.integratedDisplay) },
  { label: "Display technology", value: (product) => product.displayTechnology },
  {
    label: "Touch",
    value: (product) =>
      typeof product.touch === "boolean" ? yesNo(product.touch) : product.touch,
  },
  { label: "Control Bar", value: (product) => yesNo(product.controlBar) },
  { label: "Rotary control", value: (product) => yesNo(product.rotaryControl) },
  { label: "Haptic feedback", value: (product) => yesNo(product.haptics) },
  { label: "Apps", value: () => "Included" },
  { label: "Remote access", value: () => "Supported" },
  { label: "Backup", value: () => "Supported" },
  { label: "Storage options", value: () => "Configuration dependent" },
  { label: "Best suited to", value: (product) => product.idealFor },
] as const satisfies readonly ComparisonRow[];

export const setupSteps = [
  ["01", "Connect power", "Place the device at home and connect it."],
  ["02", "Connect to your cloud", "Join the temporary setup network."],
  ["03", "Choose your network", "The browser-based guide handles the connection."],
  ["04", "Create your account", "Set up the local administrator securely."],
  ["05", "Start using it", "Open the Web UI—no terminal required."],
] as const;

export const appCategories = [
  { code: "PH", title: "Photo library", description: "Organize and revisit your photos." },
  { code: "PW", title: "Password manager", description: "Keep essential credentials close." },
  { code: "MO", title: "Monitoring", description: "Understand what your systems are doing." },
  { code: "ME", title: "Media", description: "Bring your personal collection together." },
  { code: "FS", title: "File sync", description: "Keep important folders within reach." },
  { code: "DV", title: "Developer tools", description: "Run useful services on hardware you control." },
] as const;
