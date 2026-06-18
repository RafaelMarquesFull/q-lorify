-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_OrchFunction" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "displayName" TEXT NOT NULL,
    "description" TEXT,
    "enabled" BOOLEAN NOT NULL DEFAULT true,
    "pricePerUnit" REAL NOT NULL DEFAULT 0.0,
    "unitSize" INTEGER NOT NULL DEFAULT 1000,
    "enrichPricePerUnit" REAL NOT NULL DEFAULT 0.05,
    "enrichUnitSize" INTEGER NOT NULL DEFAULT 100000,
    "requiresAi" BOOLEAN NOT NULL DEFAULT false,
    "inputSchema" TEXT,
    "timeout" INTEGER NOT NULL DEFAULT 30000,
    "defaultModelId" TEXT,
    "fallbackModelId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);
INSERT INTO "new_OrchFunction" ("createdAt", "defaultModelId", "description", "displayName", "enabled", "fallbackModelId", "id", "inputSchema", "name", "pricePerUnit", "requiresAi", "timeout", "unitSize", "updatedAt") SELECT "createdAt", "defaultModelId", "description", "displayName", "enabled", "fallbackModelId", "id", "inputSchema", "name", "pricePerUnit", "requiresAi", "timeout", "unitSize", "updatedAt" FROM "OrchFunction";
DROP TABLE "OrchFunction";
ALTER TABLE "new_OrchFunction" RENAME TO "OrchFunction";
CREATE UNIQUE INDEX "OrchFunction_name_key" ON "OrchFunction"("name");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
