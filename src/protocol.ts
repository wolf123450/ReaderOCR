/**
 * JSON-RPC 2.0 protocol types for Tauri ↔ Python sidecar communication.
 *
 * The sidecar communicates over stdin/stdout using JSON-RPC 2.0.
 * Each line on stdin is a JSON-RPC request; each line on stdout is a response.
 */

// ---------------------------------------------------------------------------
// JSON-RPC 2.0 base types
// ---------------------------------------------------------------------------

export interface JsonRpcRequest<P = unknown> {
  jsonrpc: "2.0";
  id: number | string;
  method: string;
  params?: P;
}

export interface JsonRpcSuccessResponse<R = unknown> {
  jsonrpc: "2.0";
  id: number | string;
  result: R;
}

export interface JsonRpcErrorResponse {
  jsonrpc: "2.0";
  id: number | string | null;
  error: {
    code: number;
    message: string;
    data?: unknown;
  };
}

export type JsonRpcResponse<R = unknown> =
  | JsonRpcSuccessResponse<R>
  | JsonRpcErrorResponse;

// ---------------------------------------------------------------------------
// Standard error codes
// ---------------------------------------------------------------------------

export const JsonRpcErrorCode = {
  PARSE_ERROR: -32700,
  INVALID_REQUEST: -32600,
  METHOD_NOT_FOUND: -32601,
  INVALID_PARAMS: -32602,
  INTERNAL_ERROR: -32603,

  // Application-defined errors (-32000 to -32099)
  OCR_ENGINE_ERROR: -32001,
  IMAGE_NOT_FOUND: -32002,
  EPUB_BUILD_ERROR: -32003,
  OLLAMA_UNAVAILABLE: -32004,
} as const;

// ---------------------------------------------------------------------------
// Shared domain types
// ---------------------------------------------------------------------------

export type BlockType = "body" | "header" | "footer" | "page_number" | "table" | "figure";

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface TextBlock {
  type: BlockType;
  text: string;
  confidence: number;
  bbox: BoundingBox;
}

export interface OcrPageResult {
  page_index: number;
  blocks: TextBlock[];
  raw_text: string;
  avg_confidence: number;
}

export interface ChapterBoundary {
  page_index: number;
  title: string;
  confidence: number;
}

export interface EpubMetadata {
  title: string;
  authors: string[];
  language: string;
  publisher?: string;
  description?: string;
  isbn?: string;
  cover_image_path?: string;
}

// ---------------------------------------------------------------------------
// RPC method params & results
// ---------------------------------------------------------------------------

// ping → pong (health check)
export interface PingParams {
  timestamp?: number;
}
export interface PingResult {
  status: "ok";
  version: string;
  timestamp: number;
}

// ocr/process_page
export interface OcrProcessPageParams {
  image_path: string;
  engine?: "ppocr" | "ppocr_vl";
}
export type OcrProcessPageResult = OcrPageResult;

// ocr/preprocess_image
export interface PreprocessImageParams {
  image_path: string;
  output_path: string;
  auto_crop?: boolean;
  deskew?: boolean;
  normalize_contrast?: boolean;
}
export interface PreprocessImageResult {
  output_path: string;
  original_size: [number, number];
  processed_size: [number, number];
}

// processing/cleanup
export interface CleanupParams {
  pages: OcrPageResult[];
  remove_page_numbers?: boolean;
  remove_headers_footers?: boolean;
}
export interface CleanupResult {
  pages: OcrPageResult[];
  removed_headers: string[];
  removed_footers: string[];
}

// processing/reconstruct_paragraphs
export interface ReconstructParagraphsParams {
  pages: OcrPageResult[];
}
export interface ReconstructParagraphsResult {
  text: string;
  paragraph_breaks: number[];
}

// processing/detect_chapters
export interface DetectChaptersParams {
  pages: OcrPageResult[];
}
export interface DetectChaptersResult {
  chapters: ChapterBoundary[];
}

// epub/build
export interface EpubBuildParams {
  metadata: EpubMetadata;
  chapters: Array<{
    title: string;
    content_html: string;
  }>;
  output_path: string;
  css?: string;
}
export interface EpubBuildResult {
  output_path: string;
  file_size_bytes: number;
  chapter_count: number;
}

// ollama/postprocess (optional)
export interface OllamaPostprocessParams {
  text: string;
  task: "fix_errors" | "detect_paragraphs" | "detect_chapters";
  model?: string;
  endpoint?: string;
}
export interface OllamaPostprocessResult {
  corrected_text: string;
  changes_made: number;
}

// ---------------------------------------------------------------------------
// Method registry (for type-safe dispatch)
// ---------------------------------------------------------------------------

export interface RpcMethodMap {
  ping: { params: PingParams; result: PingResult };
  "ocr/process_page": { params: OcrProcessPageParams; result: OcrProcessPageResult };
  "ocr/preprocess_image": { params: PreprocessImageParams; result: PreprocessImageResult };
  "processing/cleanup": { params: CleanupParams; result: CleanupResult };
  "processing/reconstruct_paragraphs": {
    params: ReconstructParagraphsParams;
    result: ReconstructParagraphsResult;
  };
  "processing/detect_chapters": {
    params: DetectChaptersParams;
    result: DetectChaptersResult;
  };
  "epub/build": { params: EpubBuildParams; result: EpubBuildResult };
  "ollama/postprocess": {
    params: OllamaPostprocessParams;
    result: OllamaPostprocessResult;
  };
}
