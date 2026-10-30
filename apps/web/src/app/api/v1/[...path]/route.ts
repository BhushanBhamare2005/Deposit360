import type { NextRequest } from "next/server";

export const runtime = "nodejs";

async function forwardToApi(request: NextRequest): Promise<Response> {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return Response.json({ detail: "The API service binding is not configured." }, { status: 503 });
  }

  const target = new URL(request.nextUrl.pathname, backendUrl);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  for (const name of ["accept", "authorization", "content-type", "x-request-id"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer();
  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body,
    cache: "no-store"
  });
  const responseHeaders = new Headers();
  for (const name of ["content-disposition", "content-type", "x-request-id"]) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders
  });
}

export const GET = forwardToApi;
export const POST = forwardToApi;
export const PATCH = forwardToApi;
