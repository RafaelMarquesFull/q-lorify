import {
    IDataObject,
    INodeExecutionData,
    INodeType,
    INodeTypeDescription,
    INodePropertyOptions,
    ILoadOptionsFunctions,
    IHttpRequestOptions,
} from 'n8n-workflow';

export class Orchestrator implements INodeType {
    description: INodeTypeDescription = {
        displayName: 'Qlorify: Orquestrador',
        name: 'agentOrchestrator',
        icon: 'file:icone.png',
        group: ['transform'],
        version: 2,
        description: 'Interact with the Agent Orchestrator to execute functions based on natural language',
        defaults: {
            name: 'Qlorify: Orquestrador',
            color: '#8B5CF6',
        },
        codex: {
            categories: ['AI'],
            subcategories: {
                AI: ['Root Nodes'],
            },
        },
        // Main data input (top) + two bottom ports for credentials sub-nodes
        inputs: [
            'main' as any,
            {
                type: 'ai_tool',
                displayName: 'Credentials',
                required: true,
                maxConnections: 1,
                description: 'Connect an Agent Credentials node with primary API credentials',
            },
            {
                type: 'ai_languageModel',
                displayName: 'Fallback',
                required: false,
                maxConnections: 1,
                description: 'Connect an Agent Fallback node with backup API credentials (used when primary fails)',
            },
        ] as any,
        outputs: ['main'],
        // No built-in credential — credentials come from sub-nodes
        credentials: [],
        properties: [
            {
                displayName: 'Message',
                name: 'message',
                type: 'string',
                default: '',
                placeholder: 'Processar pedido do cliente...',
                description: 'The natural language message to send to the orchestrator',
                required: true,
            },
            {
                displayName: 'System Prompt',
                name: 'systemPrompt',
                type: 'string',
                typeOptions: {
                    rows: 6,
                },
                default: '',
                placeholder: 'Você é um especialista em extração de dados de cotações de frete...',
                description: 'Optional system prompt to guide the AI model behavior',
                required: false,
            },
            {
                displayName: 'Functions',
                name: 'functions',
                type: 'multiOptions',
                typeOptions: {
                    loadOptionsMethod: 'getFunctions',
                },
                default: [],
                description: 'Select the functions to use for processing',
                required: true,
            },
            {
                displayName: 'Output Schema (JSON)',
                name: 'outputSchema',
                type: 'json',
                default: '',
                placeholder: '{\n  "cep_origem": "",\n  "cep_destino": "",\n  "endereco_origem": {}\n}',
                description: 'Optional JSON schema defining the exact output format',
                required: false,
            },
        ],
    };

    methods = {
        loadOptions: {
            async getFunctions(this: ILoadOptionsFunctions): Promise<INodePropertyOptions[]> {
                const returnData: INodePropertyOptions[] = [];

                // Public endpoint — no auth needed.
                const baseUrls = [
                    process.env.BACKEND_API_URL || '',
                    'http://host.docker.internal:8000',
                    'http://localhost:8000',
                ].filter(Boolean);

                for (const baseUrl of baseUrls) {
                    try {
                        const options: IHttpRequestOptions = {
                            method: 'GET',
                            url: `${baseUrl}/api/public/functions`,
                            json: true,
                            timeout: 5000,
                        };

                        const response = await this.helpers.httpRequest(options);

                        if (Array.isArray(response)) {
                            for (const fn of response) {
                                returnData.push({
                                    name: fn.displayName || fn.name,
                                    value: fn.name,
                                });
                            }
                        }
                        break; // Success — stop trying other URLs
                    } catch (error) {
                        continue; // Try next URL
                    }
                }

                return returnData;
            },
        },
    } as any;

    async execute(this: any): Promise<INodeExecutionData[][]> {
        const items = this.getInputData();
        const returnData: INodeExecutionData[] = [];

        // ── Get PRIMARY credentials from Credentials port (ai_tool) ──
        let primaryCreds: any = null;
        try {
            const connectedData = await this.getInputConnectionData('ai_tool', 0);
            if (Array.isArray(connectedData)) {
                primaryCreds = connectedData[0];
            } else if (connectedData) {
                primaryCreds = connectedData;
            }
        } catch (e) {
            // No primary credentials connected
        }

        if (!primaryCreds || !primaryCreds.baseUrl || !primaryCreds.accessToken) {
            throw new Error(
                'No credentials connected. Connect an "Agent Credentials" node to the Credentials port at the bottom of this node.'
            );
        }

        const primaryBaseUrl = (primaryCreds.baseUrl as string).replace(/\/$/, '');
        const primaryToken = primaryCreds.accessToken as string;

        // ── Get FALLBACK credentials from Fallback port (ai_languageModel) ──
        let fallbackCreds: any = null;
        let fallbackBaseUrl: string | null = null;
        let fallbackToken: string | null = null;

        try {
            const fbData = await this.getInputConnectionData('ai_languageModel', 0);
            if (Array.isArray(fbData)) {
                fallbackCreds = fbData[0];
            } else if (fbData) {
                fallbackCreds = fbData;
            }

            if (fallbackCreds && fallbackCreds.baseUrl && fallbackCreds.accessToken) {
                fallbackBaseUrl = (fallbackCreds.baseUrl as string).replace(/\/$/, '');
                fallbackToken = fallbackCreds.accessToken as string;
            }
        } catch (e) {
            // No fallback connected — that's OK
        }

        // ── Model ID comes from the credentials sub-node ──
        const primaryModelId = primaryCreds.modelId as string;
        if (!primaryModelId) {
            throw new Error(
                'No Model ID configured. Open the "Agent Credentials" sub-node and select a model.'
            );
        }

        // Fallback model ID (optional — uses fallback's own model or falls back to primary's model)
        const fallbackModelId = (fallbackCreds && fallbackCreds.modelId) ? fallbackCreds.modelId as string : primaryModelId;

        // ── Process Each Item ──
        for (let i = 0; i < items.length; i++) {
            try {
                const message = this.getNodeParameter('message', i) as string;
                const systemPrompt = this.getNodeParameter('systemPrompt', i, '') as string;
                const outputSchemaRaw = this.getNodeParameter('outputSchema', i, '') as string;

                // Functions come from the Formatter's own parameter
                const functions = this.getNodeParameter('functions', i, []) as string[];
                if (!functions.length) {
                    throw new Error(
                        'No Functions selected. Select at least one function in the "Functions" field.'
                    );
                }

                const messages: IDataObject[] = [];

                if (systemPrompt) {
                    messages.push({ role: 'system', content: systemPrompt });
                }

                messages.push({ role: 'user', content: message });

                const body: IDataObject = {
                    model: primaryModelId,
                    messages,
                    functions,
                    stream: false,
                };

                // Add output_schema if provided
                if (outputSchemaRaw) {
                    try {
                        body.output_schema = JSON.parse(outputSchemaRaw);
                    } catch (e) {
                        body.output_schema = outputSchemaRaw;
                    }
                }

                // ── Helper for Retry ──
                const makeRequestWithRetry = async (url: string, token: string, bodyData: any, maxRetries = 2) => {
                    let lastError: any;
                    for (let attempt = 0; attempt <= maxRetries; attempt++) {
                        try {
                            const response = await this.helpers.httpRequest({
                                headers: {
                                    'Authorization': `Bearer ${token}`,
                                    'Content-Type': 'application/json',
                                },
                                method: 'POST',
                                body: bodyData,
                                json: true,
                                timeout: 60000,
                                url,
                            } as IHttpRequestOptions);
                            return response;
                        } catch (err: any) {
                            lastError = err;
                            if (attempt < maxRetries) {
                                // Wait before retrying (Exponential backoff: 1s, 2s)
                                await new Promise((resolve) => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                            }
                        }
                    }
                    throw lastError;
                };

                // ── Try Primary Credentials ──
                let response: any;
                let usedFallback = false;

                try {
                    response = await makeRequestWithRetry(`${primaryBaseUrl}/api/chat/completions`, primaryToken, body);
                } catch (primaryError: any) {
                    // ── Try Fallback if available ──
                    if (fallbackBaseUrl && fallbackToken) {
                        try {
                            const fallbackBody = { ...body, model: fallbackModelId };
                            response = await makeRequestWithRetry(`${fallbackBaseUrl}/api/chat/completions`, fallbackToken, fallbackBody);
                            usedFallback = true;
                        } catch (fallbackError: any) {
                            throw new Error(
                                `Both primary and fallback credentials failed.\n` +
                                `Primary [${primaryCreds.label || 'Primary'}]: ${primaryError.message}\n` +
                                `Fallback [${fallbackCreds?.label || 'Fallback'}]: ${fallbackError.message}`
                            );
                        }
                    } else {
                        throw primaryError;
                    }
                }

                const item = items[i];
                item.json = response;

                // Metadata about credential usage
                item.json._credentialInfo = {
                    usedFallback,
                    primaryLabel: primaryCreds.label || 'Primary',
                    fallbackLabel: fallbackCreds?.label || null,
                    fallbackAvailable: !!fallbackCreds,
                };

                // Extract assistant message content
                if (response.choices && response.choices[0] && response.choices[0].message) {
                    try {
                        item.json.responseContent = JSON.parse(response.choices[0].message.content);
                    } catch (e) {
                        item.json.responseContent = response.choices[0].message.content;
                    }
                }

                returnData.push(item);
            } catch (error: any) {
                if (this.continueOnFail()) {
                    items[i].json = { error: error.message };
                    returnData.push(items[i]);
                    continue;
                }
                throw error;
            }
        }

        return this.prepareOutputData(returnData) as any;
    }
}
