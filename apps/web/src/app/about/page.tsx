import type { Metadata } from "next";
import { OffAttribution } from "@/components/off-attribution";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return (
    <article className="flex max-w-2xl flex-col gap-4">
      <h1 className="font-display text-2xl font-bold">About CookToFit</h1>
      <p>
        A home-cooking and nutrition coach that lives in WhatsApp. It works out your targets, suggests
        dishes from your pantry, and logs meals from a photo or a quick text.
      </p>
      <h2 className="font-display text-lg font-semibold">Data sources</h2>
      <ul className="list-disc space-y-2 pl-5 text-sm">
        <li>
          <OffAttribution />
        </li>
        <li>Indian Food Composition Tables (IFCT 2017), ICMR-National Institute of Nutrition.</li>
        <li>USDA FoodData Central (public domain).</li>
      </ul>
    </article>
  );
}
