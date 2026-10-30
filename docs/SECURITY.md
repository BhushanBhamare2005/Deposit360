# Security notes

- Generate a unique `SECRET_KEY` for each environment. Do not commit `.env` files.
- Passwords use salted PBKDF2-HMAC-SHA256 hashes and constant-time verification.
- API access tokens are signed and expire according to `ACCESS_TOKEN_EXPIRE_MINUTES`.
- The browser keeps the bearer token in session storage and removes it at sign-out.
- Institution users can only read and create records for their linked institution.
- PDF files are size-limited, signature-checked, and stored under generated names.
- Do not expose the upload directory directly from the web server.
- Use HTTPS, managed secrets, database backups, and a private upload store in
  production. Local disk storage and self-registration are intended for the MVP.

The initial self-registration flow grants only the institution-user role. Reviewer
and admin accounts are provisioned through the interactive CLI, not a public API.