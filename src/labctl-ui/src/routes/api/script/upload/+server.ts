import { mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";

import { json } from "@sveltejs/kit";

function sanitizeFilename(filename: string) {
  return basename(filename).replace(/[^a-zA-Z0-9._-]/g, "_");
}

export async function POST({ request }) {
  try {
    const formData = await request.formData();
    const uploaded = formData.get("script");

    if (!(uploaded instanceof File)) {
      return json({ message: "No script file was provided." }, { status: 400 });
    }

    if (!uploaded.name.toLowerCase().endsWith(".labctl")) {
      return json({ message: "Only .labctl script files are supported." }, { status: 400 });
    }

    const scriptsDir = join(tmpdir(), "labctl-ui-scripts");
    await mkdir(scriptsDir, { recursive: true });

    const safeName = sanitizeFilename(uploaded.name);
    const targetPath = join(scriptsDir, `${Date.now()}-${safeName}`);

    await writeFile(targetPath, Buffer.from(await uploaded.arrayBuffer()));

    return json({
      fileName: uploaded.name,
      path: targetPath
    });
  } catch (error) {
    return json(
      {
        message: error instanceof Error ? error.message : "Failed to upload the script."
      },
      { status: 500 }
    );
  }
}
