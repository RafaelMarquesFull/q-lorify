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
        // Main data input (left) + two bottom ports for credentials sub-nodes
        inputs: ['main', 'ai_tool', 'ai_tool'] as any,
        outputs: ['main'],
        // No built-in credential — credentials come from sub-nodes
        credentials: [],
        properties: [
            {
                displayName: 'Model ID',
                name: 'modelId',
                type: 'options',
                typeOptions: {
                    loadOptionsMethod: 'getModels',
                },
                default: '',
                description: 'Select the AI model to use',
                required: true,
            },
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
            async getModels(this: ILoadOptionsFunctions): Promise<INodePropertyOptions[]> {
                const returnData: INodePropertyOptions[] = [];
                const baseUrls = [
                    process.env.QLORIFY_BASE_URL || process.env.BACKEND_API_URL || '',
                    'http://host.docker.internal:8000',
                    'http://localhost:8000',
                ].filter(Boolean);

                for (const baseUrl of baseUrls) {
                    try {
                        const options: IHttpRequestOptions = {
                            method: 'GET',
                            url: `${baseUrl}/api/public/models`,
                            json: true,
                            timeout: 5000,
                        };
                        const response = await this.helpers.httpRequest(options);
                        if (Array.isArray(response)) {
                            for (const model of response) {
                                if (model.isOrchestrator) {
                                    returnData.push({
                                        name: `${model.name} (${model.provider || 'Agent'})`,
                                        value: model.id,
                                    });
                                }
                            }
                        }
                        break;
                    } catch (error) {
                        continue;
                    }
                }
                return returnData;
            },
            async getFunctions(this: ILoadOptionsFunctions): Promise<INodePropertyOptions[]> {
                const returnData: INodePropertyOptions[] = [];
                const modelId = this.getCurrentNodeParameter('modelId') as string;
                
                if (!modelId) {
                    return [{ name: 'Please select a Model first', value: '' }];
                }

                const baseUrls = [
                    process.env.QLORIFY_BASE_URL || process.env.BACKEND_API_URL || '',
                    'http://host.docker.internal:8000',
                    'http://localhost:8000',
                ].filter(Boolean);

                for (const baseUrl of baseUrls) {
                    try {
                        const options: IHttpRequestOptions = {
                            method: 'GET',
                            url: `${baseUrl}/api/public/functions?model_id=${modelId}`,
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
                        break;
                    } catch (error) {
                        continue;
                    }
                }

                return returnData;
            },
        },
    } as any;

    async execute(this: any): Promise<INodeExecutionData[][]> {
        const items = this.getInputData();
        const returnData: INodeExecutionData[] = [];

        // ── Get PRIMARY credentials from Credentials port (ai_tool index 0) ──
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
                'No credentials connected. Connect a "Qlorify Credentials" node to the Credentials port.'
            );
        }

        const primaryBaseUrl = (primaryCreds.baseUrl as string).replace(/\/$/, '');
        const primaryToken = primaryCreds.accessToken as string;

        // ── Get FALLBACK credentials from Fallback port (ai_tool index 1) ──
        let fallbackCreds: any = null;
        let fallbackBaseUrl: string | null = null;
        let fallbackToken: string | null = null;

        try {
            const fbData = await this.getInputConnectionData('ai_tool', 1);
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

        // Fallback info exists only if fallback is connected

        // ── Process Each Item ──
        for (let i = 0; i < items.length; i++) {
            try {
                const primaryModelId = this.getNodeParameter('modelId', i) as string;
                const fallbackModelId = primaryModelId;
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

                // Add output_schema if provided and not completely empty
                if (outputSchemaRaw && outputSchemaRaw.trim() !== '' && outputSchemaRaw.trim() !== '{}') {
                    try {
                        const parsed = JSON.parse(outputSchemaRaw);
                        if (typeof parsed === 'object' && parsed !== null && Object.keys(parsed).length > 0) {
                            body.output_schema = parsed;
                        }
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
