import { describe, expect, it } from "vitest";
import i18n, { applyUILanguage, I18N_RESOURCES, RTL_LOCALES } from "@/i18n";
import { en } from "@/i18n/resources/en";
import { hi } from "@/i18n/resources/hi";
import { ta } from "@/i18n/resources/ta";
import { te } from "@/i18n/resources/te";
import { bn } from "@/i18n/resources/bn";
import { kn } from "@/i18n/resources/kn";
import { ml } from "@/i18n/resources/ml";
import { gu } from "@/i18n/resources/gu";
import { mr } from "@/i18n/resources/mr";
import { pa } from "@/i18n/resources/pa";
import { or } from "@/i18n/resources/or";
import { as } from "@/i18n/resources/as";
import { ur } from "@/i18n/resources/ur";
import { SUPPORTED_UI_LANGUAGES } from "@/lib/constants";

const LOCALES: Record<string, Record<string, unknown>> = {
  en,
  hi,
  ta,
  te,
  bn,
  kn,
  ml,
  gu,
  mr,
  pa,
  or,
  as,
  ur,
};

/** Collect every leaf key as a dotted path, e.g. "chat.emptyTitle". */
function flattenKeys(obj: Record<string, unknown>, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return value && typeof value === "object" && !Array.isArray(value)
      ? flattenKeys(value as Record<string, unknown>, path)
      : [path];
  });
}

describe("i18n resources", () => {
  it("registers all 13 supported UI languages", () => {
    const supported = SUPPORTED_UI_LANGUAGES.map((l) => l.code);
    expect(Object.keys(I18N_RESOURCES).sort()).toEqual(supported.sort());
  });

  it.each(Object.keys(LOCALES))("locale %s has the same key tree as English", (code) => {
    const englishKeys = new Set(flattenKeys(en));
    const localeKeys = new Set(flattenKeys(LOCALES[code]));
    expect(localeKeys.size).toBe(englishKeys.size);
    for (const key of englishKeys) {
      expect(localeKeys.has(key), `missing key "${key}" in ${code}`).toBe(true);
    }
  });

  it("localised copy differs from English except brand/loan tokens", () => {
    // Words that legitimately stay as-is across locales (brand names,
    // acronyms and the i18next interpolation token).
    const allowed = new Set([
      "Google",
      "CSC",
      "OCR",
      "count",
      "PDF",
      "JPG",
      "PNG",
      "MB",
      "CiviServe",
    ]);
    for (const code of ["hi", "ta", "bn", "ur", "ml"]) {
      const ref = flattenKeys(en);
      for (const key of ref) {
        const valueAt = (tree: Record<string, unknown>): string =>
          String(
            key.split(".").reduce<unknown>(
              (acc, part) => (acc as Record<string, unknown>)[part],
              tree,
            ),
          );
        const english = valueAt(en);
        const local = valueAt(LOCALES[code]);
        if (english === local) continue;
        const latinRuns = local.match(/[A-Za-z]{3,}/g) ?? [];
        const unexpected = latinRuns.filter((word) => !allowed.has(word));
        expect(
          unexpected,
          `untranslated English text "${local}" (key "${key}") in ${code}`,
        ).toHaveLength(0);
      }
    }
  });
});

describe("RTL handling", () => {
  it("marks Urdu as RTL and everything else LTR", () => {
    expect(RTL_LOCALES.has("ur")).toBe(true);
    expect(RTL_LOCALES.has("hi")).toBe(false);
    expect(RTL_LOCALES.has("en")).toBe(false);
  });

  it("sets documentElement.dir to rtl for Urdu via applyUILanguage", async () => {
    await applyUILanguage("ur");
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ur");
    expect(i18n.language).toBe("ur");
  });

  it("sets documentElement.dir back to ltr for Hindi", async () => {
    await applyUILanguage("hi");
    expect(document.documentElement.dir).toBe("ltr");
    expect(i18n.language).toBe("hi");
  });
});
