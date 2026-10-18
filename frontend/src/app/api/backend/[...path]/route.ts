import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

const MAX_REQUEST_BYTES = 11 * 1024 * 1024;
const HOP_BY_HOP_HEADERS = [
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
];

function backendOrigin(): string {
  const configured = process.env.INTERNAL_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL;
  const url = new URL(configured ?? "http://127.0.0.1:8000");
  if (url.hostname === "localhost") url.hostname = "127.0.0.1";
  return url.origin;
}

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (declaredLength > MAX_REQUEST_BYTES) {
    return NextResponse.json({ detail: "Ukuran unggahan maksimal 10 MB" }, { status: 413 });
  }

  const { path } = await context.params;
  const target = new URL(`/${path.map(encodeURIComponent).join("/")}`, backendOrigin());
  target.search = request.nextUrl.search;
  const appraisalStream = target.pathname === "/borrower/v1/estimates/stream";

  const headers = new Headers(request.headers);
  for (const header of HOP_BY_HOP_HEADERS) headers.delete(header);

  const hasBody = !["GET", "HEAD"].includes(request.method);
  const body = hasBody ? await request.arrayBuffer() : undefined;
  if (body && body.byteLength > MAX_REQUEST_BYTES) {
    return NextResponse.json({ detail: "Ukuran unggahan maksimal 10 MB" }, { status: 413 });
  }

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      redirect: "manual",
      cache: "no-store",
      signal: AbortSignal.timeout(appraisalStream ? 300_000 : 150_000),
    });
    const responseHeaders = new Headers(upstream.headers);
    responseHeaders.delete("content-length");
    responseHeaders.delete("transfer-encoding");

    const response = new NextResponse(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
    const getSetCookie = (upstream.headers as Headers & { getSetCookie?: () => string[] }).getSetCookie;
    if (getSetCookie) {
      response.headers.delete("set-cookie");
      for (const cookie of getSetCookie.call(upstream.headers)) response.headers.append("set-cookie", cookie);
    }
    return response;
  } catch (error) {
    const timedOut = error instanceof Error && error.name === "TimeoutError";
    return NextResponse.json(
      { detail: timedOut ? (appraisalStream ? "Analisis barang melewati batas waktu 300 detik" : "Proses OCR melewati batas waktu 150 detik") : "Backend PrivGadai memutus koneksi" },
      { status: 502 },
    );
  }
}

export { proxy as DELETE, proxy as GET, proxy as HEAD, proxy as OPTIONS, proxy as PATCH, proxy as POST, proxy as PUT };
