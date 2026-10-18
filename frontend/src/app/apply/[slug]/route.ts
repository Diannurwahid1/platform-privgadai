export function GET(request: Request) {
  return Response.redirect(new URL("/borrower/apply", request.url), 307);
}
