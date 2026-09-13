# Klyrow TypeScript client

The existing fetch-based client now exposes typed template history:

```ts
import { Klyrow } from "./src/index";

const client = new Klyrow(token);
const page = await client.templateVersions(templateId, { limit: 25 });
const version = await client.templateVersion(templateId, page.items[0].id);
```

`src/schema.d.ts` is generated from the implemented public OpenAPI export.
Regenerate after changing API handlers:

```sh
python scripts/export-api-contracts.py
npx --yes --package=openapi-typescript@7.10.1 openapi-typescript schemas/openapi/klyrow-public-api.yaml -o sdk/typescript/src/schema.d.ts
npx --yes --package=typescript@5.9.2 tsc --noEmit --strict --lib es2022,dom sdk/typescript/src/index.ts
```

Run commands from the repository root. CI regenerates to a temporary file,
compares the result and compiles the client against it. Existing send/message
methods keep their current contract; generated types do not imply that every
target-blueprint endpoint has been implemented.
