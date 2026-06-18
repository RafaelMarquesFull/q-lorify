-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_SentimentLog" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "domain" TEXT NOT NULL DEFAULT 'transport',
    "timestamp" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "intent" TEXT NOT NULL,
    "context" TEXT,
    "categories" TEXT NOT NULL,
    "classification" TEXT NOT NULL,
    "classifications" TEXT,
    "confidence" REAL NOT NULL DEFAULT 0.0,
    "source" TEXT NOT NULL,
    "tokenUsage" INTEGER NOT NULL DEFAULT 0,
    "executionTimeMs" INTEGER NOT NULL DEFAULT 0,
    "isReviewed" BOOLEAN NOT NULL DEFAULT false,
    "adminCorrection" TEXT,
    "reviewedBy" TEXT,
    "reviewedAt" DATETIME,
    "feedbackNotes" TEXT,
    CONSTRAINT "SentimentLog_domain_fkey" FOREIGN KEY ("domain") REFERENCES "DomainConfig" ("domain") ON DELETE RESTRICT ON UPDATE CASCADE
);
INSERT INTO "new_SentimentLog" ("adminCorrection", "categories", "classification", "classifications", "confidence", "context", "domain", "feedbackNotes", "id", "intent", "isReviewed", "reviewedAt", "reviewedBy", "source", "timestamp", "tokenUsage") SELECT "adminCorrection", "categories", "classification", "classifications", "confidence", "context", "domain", "feedbackNotes", "id", "intent", "isReviewed", "reviewedAt", "reviewedBy", "source", "timestamp", "tokenUsage" FROM "SentimentLog";
DROP TABLE "SentimentLog";
ALTER TABLE "new_SentimentLog" RENAME TO "SentimentLog";
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
