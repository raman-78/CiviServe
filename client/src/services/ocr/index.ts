/**
 * OCR adapter (docs/architecture/17 swap point).
 *
 * Feature code depends on the `OcrAdapter` interface only. The MVP uses
 * tesseract.js in the browser and pushes the extracted text to the server for
 * document-type detection (the server never runs OCR itself — no PaddleOCR
 * endpoint is configured). Swapping to a server-side engine means changing the
 * factory + implementation; the feature layer stays untouched.
 */

export type OcrErrorCode = "unavailable" | "load-failed" | "recognize-failed" | "aborted";

export interface OcrAdapter {
  /** True when the OCR engine can run (e.g. tesseract loads, wasm allowed). */
  readonly isSupported: boolean;
  /**
   * Recognize text from an image file. Returns raw OCR text; the caller is
   * responsible for sending it to the server for type detection.
   */
  recognize(file: File | Blob): Promise<string>;
  /** Pre-load the engine/workers and warm the language model. */
  warmup(): Promise<void>;
  /** Abort in-flight recognition. */
  cancel(): void;
  onError(cb: (code: OcrErrorCode) => void): () => void;
}

/** Factory behind `VITE_OCR_ENGINE`. Defaults to the browser tesseract engine. */
export function createOcrAdapter(): OcrAdapter {
  const engine = import.meta.env.VITE_OCR_ENGINE ?? "tesseract";
  if (engine === "paddle") {
    // Server-side PaddleOCR is a declared swap point; no client SDK wired yet.
    return new UnavailableOcrAdapter();
  }
  return new TesseractOcrAdapter();
}

class OcrCancelledError extends Error {
  constructor() {
    super("OCR cancelled.");
    this.name = "OcrCancelledError";
  }
}

/** Minimal typing for tesseract.js so heavy imports stay dynamic. */
interface TesseractModule {
  createWorker(lang: string): Promise<{ recognize: (i: File | Blob) => Promise<{ data: { text?: string } }>; terminate: () => Promise<void> }>;
}
type TesseractLoader = () => Promise<TesseractModule>;

class TesseractOcrAdapter implements OcrAdapter {
  readonly isSupported: boolean;
  private enginePromise: TesseractLoader | null = null;
  private cancelled = false;
  private errorCbs: ((code: OcrErrorCode) => void)[] = [];

  constructor() {
    this.isSupported = typeof window !== "undefined" && typeof Worker !== "undefined";
  }

  private async engine(): Promise<TesseractModule> {
    if (!this.enginePromise) {
      // Dynamic import keeps tesseract.js (and its wasm workers) out of the
      // main bundle until OCR is actually used.
      this.enginePromise = import("tesseract.js") as unknown as TesseractLoader;
    }
    return this.enginePromise();
  }

  async warmup(): Promise<void> {
    if (!this.isSupported) {
      this.emit("unavailable");
      return;
    }
    try {
      const Tesseract = await this.engine();
      const worker = await Tesseract.createWorker("eng");
      await worker.terminate();
    } catch {
      this.emit("load-failed");
    }
  }

  async recognize(file: File | Blob): Promise<string> {
    if (!this.isSupported) {
      this.emit("unavailable");
      throw new OcrCancelledError();
    }
    this.cancelled = false;
    try {
      const Tesseract = await this.engine();
      const worker = await Tesseract.createWorker("eng");
      try {
        if (this.cancelled) throw new OcrCancelledError();
        const { data } = await worker.recognize(file);
        return (data.text ?? "").trim();
      } finally {
        await worker.terminate();
      }
    } catch (error) {
      if (error instanceof OcrCancelledError || this.cancelled) {
        this.emit("aborted");
      } else {
        this.emit("recognize-failed");
      }
      throw error;
    }
  }

  cancel(): void {
    this.cancelled = true;
  }

  onError(cb: (code: OcrErrorCode) => void): () => void {
    this.errorCbs.push(cb);
    return () => {
      this.errorCbs = this.errorCbs.filter((f) => f !== cb);
    };
  }

  private emit(code: OcrErrorCode) {
    this.errorCbs.forEach((cb) => cb(code));
  }
}

class UnavailableOcrAdapter implements OcrAdapter {
  readonly isSupported = false;
  private errorCbs: ((code: OcrErrorCode) => void)[] = [];

  async recognize(): Promise<string> {
    this.emit("unavailable");
    throw new OcrCancelledError();
  }
  async warmup(): Promise<void> {}
  cancel(): void {}
  onError(cb: (code: OcrErrorCode) => void): () => void {
    this.errorCbs.push(cb);
    return () => {
      this.errorCbs = this.errorCbs.filter((f) => f !== cb);
    };
  }
  private emit(code: OcrErrorCode) {
    this.errorCbs.forEach((cb) => cb(code));
  }
}

/** Shared long-lived instance so feature code registers once. */
export const ocrAdapter = createOcrAdapter();