import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "CookToFit",
    short_name: "CookToFit",
    description: "Every meal is a rep.",
    start_url: "/",
    display: "standalone",
    background_color: "#2A1E18",
    theme_color: "#2A1E18",
    icons: [
      { src: "/pwa-192.png", sizes: "192x192", type: "image/png" },
      { src: "/pwa-512.png", sizes: "512x512", type: "image/png" },
      { src: "/pwa-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
