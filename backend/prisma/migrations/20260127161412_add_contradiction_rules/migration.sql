-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "email" TEXT NOT NULL,
    "password" TEXT NOT NULL,
    "name" TEXT,
    "role" TEXT NOT NULL DEFAULT 'CLIENT',
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "balance" REAL NOT NULL DEFAULT 0.0,
    "stripeCustomerId" TEXT,
    "stripePaymentMethodId" TEXT,
    "autoRechargeEnabled" BOOLEAN NOT NULL DEFAULT false,
    "rechargeThreshold" REAL NOT NULL DEFAULT 10.0,
    "rechargeAmount" REAL NOT NULL DEFAULT 50.0
);

-- CreateTable
CREATE TABLE "AIProvider" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "baseUrl" TEXT,
    "apiKey" TEXT,
    "type" TEXT NOT NULL,
    "rotationEnabled" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "ProviderApiKey" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "providerId" TEXT NOT NULL,
    "apiKey" TEXT NOT NULL,
    "label" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "usageCount" INTEGER NOT NULL DEFAULT 0,
    "lastUsedAt" DATETIME,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "ProviderApiKey_providerId_fkey" FOREIGN KEY ("providerId") REFERENCES "AIProvider" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "AIModel" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "providerModelId" TEXT,
    "providerId" TEXT NOT NULL,
    "costPerInputToken" REAL NOT NULL DEFAULT 0.0,
    "costPerOutputToken" REAL NOT NULL DEFAULT 0.0,
    "description" TEXT,
    "rpm" INTEGER NOT NULL DEFAULT 60,
    "integrationGuide" TEXT,
    "isPublic" BOOLEAN NOT NULL DEFAULT true,
    "fallback1Id" TEXT,
    "fallback2Id" TEXT,
    "fallback3Id" TEXT,
    "isOrchestrator" BOOLEAN NOT NULL DEFAULT false,
    "isSentiment" BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT "AIModel_providerId_fkey" FOREIGN KEY ("providerId") REFERENCES "AIProvider" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Agent" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "systemPrompt" TEXT NOT NULL,
    "modelId" TEXT NOT NULL,
    "userId" TEXT,
    "config" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "Agent_modelId_fkey" FOREIGN KEY ("modelId") REFERENCES "AIModel" ("id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "Agent_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "ApiKey" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "key" TEXT NOT NULL,
    "name" TEXT,
    "userId" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "active" BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT "ApiKey_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Metric" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "modelId" TEXT,
    "inputTokens" INTEGER NOT NULL DEFAULT 0,
    "outputTokens" INTEGER NOT NULL DEFAULT 0,
    "cost" REAL NOT NULL DEFAULT 0.0,
    "requestDurationMs" INTEGER,
    "timestamp" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Metric_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "Metric_modelId_fkey" FOREIGN KEY ("modelId") REFERENCES "AIModel" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Subscription" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "stripeCustomerId" TEXT,
    "stripeSubscriptionId" TEXT,
    "status" TEXT NOT NULL DEFAULT 'inactive',
    "plan" TEXT,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "Subscription_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "AffiliateProfile" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "balance" REAL NOT NULL DEFAULT 0.0,
    "commissionRate" REAL NOT NULL DEFAULT 0.1,
    "referralCode" TEXT NOT NULL,
    CONSTRAINT "AffiliateProfile_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "AffiliateTransaction" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "affiliateId" TEXT NOT NULL,
    "amount" REAL NOT NULL,
    "type" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "AffiliateTransaction_affiliateId_fkey" FOREIGN KEY ("affiliateId") REFERENCES "AffiliateProfile" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Transaction" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "amount" REAL NOT NULL,
    "description" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Transaction_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "OrchFunction" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "displayName" TEXT NOT NULL,
    "description" TEXT,
    "enabled" BOOLEAN NOT NULL DEFAULT true,
    "pricePerUnit" REAL NOT NULL DEFAULT 0.0,
    "unitSize" INTEGER NOT NULL DEFAULT 1000,
    "requiresAi" BOOLEAN NOT NULL DEFAULT false,
    "inputSchema" TEXT,
    "timeout" INTEGER NOT NULL DEFAULT 30000,
    "defaultModelId" TEXT,
    "fallbackModelId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "OrchClient" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "token" TEXT NOT NULL,
    "enabled" BOOLEAN NOT NULL DEFAULT true,
    "rateLimit" INTEGER NOT NULL DEFAULT 100,
    "allowedFunctions" TEXT,
    "allowedModels" TEXT,
    "requestCount" INTEGER NOT NULL DEFAULT 0,
    "lastRequestAt" DATETIME,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "OrchExecution" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "clientId" TEXT,
    "userId" TEXT,
    "functionName" TEXT NOT NULL,
    "input" TEXT NOT NULL,
    "output" TEXT,
    "success" BOOLEAN NOT NULL,
    "usedAi" BOOLEAN NOT NULL DEFAULT false,
    "modelUsed" TEXT,
    "cost" TEXT NOT NULL DEFAULT 'low',
    "durationMs" INTEGER NOT NULL,
    "error" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "UserFunction" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "functionName" TEXT NOT NULL,
    "enabled" BOOLEAN NOT NULL DEFAULT true,
    "outputTemplate" TEXT,
    "config" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "UserFunctionKey" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "functionName" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "DomainConfig" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "domain" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "icon" TEXT,
    "defaultCategories" TEXT NOT NULL,
    "systemPrompt" TEXT NOT NULL,
    "matchingRules" TEXT,
    "contradictionRules" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "isDefault" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "SentimentLog" (
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
    "isReviewed" BOOLEAN NOT NULL DEFAULT false,
    "adminCorrection" TEXT,
    "reviewedBy" TEXT,
    "reviewedAt" DATETIME,
    "feedbackNotes" TEXT,
    CONSTRAINT "SentimentLog_domain_fkey" FOREIGN KEY ("domain") REFERENCES "DomainConfig" ("domain") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "SentimentSynonym" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "domain" TEXT NOT NULL DEFAULT 'transport',
    "word" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "source" TEXT NOT NULL DEFAULT 'admin',
    "approvedBy" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "useCount" INTEGER NOT NULL DEFAULT 0,
    "lastUsedAt" DATETIME,
    CONSTRAINT "SentimentSynonym_domain_fkey" FOREIGN KEY ("domain") REFERENCES "DomainConfig" ("domain") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "SentimentPattern" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "domain" TEXT NOT NULL DEFAULT 'transport',
    "word" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "occurrenceCount" INTEGER NOT NULL DEFAULT 1,
    "avgConfidence" REAL NOT NULL DEFAULT 0.0,
    "lastSeen" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "autoApproved" BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT "SentimentPattern_domain_fkey" FOREIGN KEY ("domain") REFERENCES "DomainConfig" ("domain") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE UNIQUE INDEX "ApiKey_key_key" ON "ApiKey"("key");

-- CreateIndex
CREATE UNIQUE INDEX "Subscription_userId_key" ON "Subscription"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "AffiliateProfile_userId_key" ON "AffiliateProfile"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "AffiliateProfile_referralCode_key" ON "AffiliateProfile"("referralCode");

-- CreateIndex
CREATE UNIQUE INDEX "OrchFunction_name_key" ON "OrchFunction"("name");

-- CreateIndex
CREATE UNIQUE INDEX "OrchClient_token_key" ON "OrchClient"("token");

-- CreateIndex
CREATE UNIQUE INDEX "UserFunction_userId_functionName_key" ON "UserFunction"("userId", "functionName");

-- CreateIndex
CREATE UNIQUE INDEX "UserFunctionKey_userId_functionName_key_key" ON "UserFunctionKey"("userId", "functionName", "key");

-- CreateIndex
CREATE UNIQUE INDEX "DomainConfig_domain_key" ON "DomainConfig"("domain");

-- CreateIndex
CREATE UNIQUE INDEX "SentimentSynonym_domain_word_category_key" ON "SentimentSynonym"("domain", "word", "category");

-- CreateIndex
CREATE UNIQUE INDEX "SentimentPattern_domain_word_category_key" ON "SentimentPattern"("domain", "word", "category");
