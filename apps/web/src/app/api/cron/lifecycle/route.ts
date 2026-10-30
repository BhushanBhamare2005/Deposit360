import type { NextRequest } from "next/server";

export const runtime = "nodejs";

export async function GET(request: NextRequest): Promise<Response> {
  const cronSecret = process.env.CRON_SECRET;
  const authorization = request.headers.get("authorization");
  if (!cronSecret) {
    return Response.json({ detail: "Lifecycle cron is not configured." }, { status: 503 });
  }
  if (authorization !== `Bearer ${cronSecret}`) {
    return Response.json({ detail: "Unauthorized." }, { status: 401 });
  }

  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return Response.json({ detail: "The API service binding is not configured." }, { status: 503 });
  }
  const upstream = await fetch(new URL("/internal/lifecycle/refresh", backendUrl), {
    method: "POST",
    headers: { authorization },
    cache: "no-store"
  });
  const headers = new Headers();
  const contentType = upstream.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  return new Response(upstream.body, { status: upstream.status, headers });
}
