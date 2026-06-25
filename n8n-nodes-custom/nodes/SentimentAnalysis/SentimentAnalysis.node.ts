import {
    IExecuteFunctions,
    ILoadOptionsFunctions,
} from 'n8n-core';

import {
    IDataObject,
    INodeExecutionData,
    INodePropertyOptions,
    INodeType,
    INodeTypeDescription,
    IHttpRequestOptions,
} from 'n8n-workflow';

export class SentimentAnalysis implements INodeType {
    description: INodeTypeDescription = {
        displayName: 'Qlorify: Análise de Sentimento',
        name: 'sentimentAnalysis',
        icon: 'file:icone.png',
        group: ['transform'],
        version: 1,
        description: 'Analyze sentiment using the Agent Orchestrator with Domain Learning',
        defaults: {
            name: 'Qlorify: Análise de Sentimento',
            color: '#8B5CF6',
        },
        inputs: [
            'main' as any,
            {
                type: 'ai_tool',
                displayName: 'Credentials',
                required: true,
                maxConnections: 1,
                description: 'Connect a Qlorify Credentials node for primary API access',
            },
            {
                type: 'ai_tool',
                displayName: 'Fallback',
                required: false,
                maxConnections: 1,
                description: 'Connect a Qlorify Credentials node for backup API access',
            },
        ] as any,
        outputs: ['main'],
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
                displayName: 'Domain',
                name: 'domain',
                type: 'options',
                default: 'transport',
                required: true,
                description: 'Select the knowledge domain for specialized analysis',
                options: [
                    {
                        name: '🚚 Transport & Logistics',
                        value: 'transport',
                        description: 'Quotes, tracking, deliveries, fiscal docs'
                    },
                    {
                        name: '🏥 Health & Medicine',
                        value: 'health',
                        description: 'Appointments, exams, prescriptions'
                    },
                    {
                        name: '🍔 Food & Delivery',
                        value: 'food',
                        description: 'Orders, menu, delivery, reservations'
                    },
                    {
                        name: '🏪 E-commerce & Retail',
                        value: 'ecommerce',
                        description: 'Products, purchases, returns, support'
                    },
                    {
                        name: '🚗 Automotive',
                        value: 'automotive',
                        description: 'Services, parts, quotes, documentation'
                    },
                    {
                        name: '⚙️ Custom',
                        value: 'custom',
                        description: 'Use custom categories only'
                    }
                ],
            },
            {
                displayName: 'Intention (User Message)',
                name: 'intention',
                type: 'string',
                default: '',
                placeholder: '{{ $json.message }}',
                description: 'The user message to be classified.',
                required: true,
                typeOptions: {
                    rows: 2,
                },
            },
            {
                displayName: 'Context (Chat History)',
                name: 'context',
                type: 'string',
                default: '',
                placeholder: 'Previous messages or context',
                description: 'Context for the AI to understand the conversation flow.',
                typeOptions: {
                    rows: 3,
                },
            },
            {
                displayName: 'Status Verify (JSON)',
                name: 'status',
                type: 'string',
                default: '',
                placeholder: '{{ $json.status }}',
                description: 'Current execution status (JSON or String).',
            },
            {
                displayName: 'Categories (Optional)',
                name: 'categories',
                type: 'string',
                default: '',
                placeholder: 'Leave empty to use Domain defaults',
                description: 'Override domain categories. Comma separated.',
            },
            {
                displayName: 'Advanced Options',
                name: 'options',
                type: 'collection',
                placeholder: 'Add Option',
                default: {},
                options: [
                    {
                        displayName: 'System Prompt',
                        name: 'systemPrompt',
                        type: 'string',
                        default: '',
                        typeOptions: {
                            rows: 4,
                        },
                        description: 'Override system prompt for AI analysis',
                    },
                    {
                        displayName: 'Menu Classification',
                        name: 'menuOptions',
                        placeholder: 'Add Menu Option',
                        type: 'fixedCollection',
                        typeOptions: {
                            multipleValues: true,
                        },
                        default: {},
                        options: [
                            {
                                name: 'option',
                                displayName: 'Option',
                                values: [
                                    {
                                        displayName: 'ID',
                                        name: 'id',
                                        type: 'string',
                                        default: '',
                                        description: 'The numeric or keyword ID (e.g., "1")',
                                    },
                                    {
                                        displayName: 'Valid Value',
                                        name: 'value',
                                        type: 'string',
                                        default: '',
                                        description: 'The internal value to return (e.g., "financeiro")',
                                    },
                                    {
                                        displayName: 'Description',
                                        name: 'description',
                                        type: 'string',
                                        default: '',
                                        description: 'Description for AI context (e.g., "Contas a pagar")',
                                    },
                                ],
                            },
                        ],
                        description: 'Define allowed menu options for AI classification',
                    },
                    {
                        displayName: 'Exceptions',
                        name: 'exceptions',
                        placeholder: 'Add Exception',
                        type: 'fixedCollection',
                        typeOptions: {
                            multipleValues: true,
                        },
                        default: {},
                        options: [
                            {
                                name: 'exception',
                                displayName: 'Exception',
                                values: [
                                    {
                                        displayName: 'Pattern',
                                        name: 'pattern',
                                        type: 'string',
                                        default: '',
                                        placeholder: 'encerrar, finalizar, sair',
                                        description: 'Keywords (comma-separated) or regex. Ex: "atendente, humano, pessoa"',
                                    },
                                    {
                                        displayName: 'Action',
                                        name: 'action',
                                        type: 'string',
                                        default: 'reclassify',
                                        description: 'Action to take (default: "reclassify")',
                                    },
                                ],
                            },
                        ],
                        description: 'Define patterns that force reclassification regardless of context',
                    },
                ],
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
                                const orqTag = model.isOrchestrator ? 'Orq' : '';
                                const sentTag = model.isSentiment ? 'Sent' : '';
                                const tags = [orqTag, sentTag].filter(Boolean).join(' | ');
                                returnData.push({
                                    name: `${model.name} (${model.provider || 'Agent'}) [${tags}]`,
                                    value: model.id,
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

        const baseUrl = (primaryCreds.baseUrl as string).replace(/\/$/, '');
        const token = primaryCreds.accessToken as string;

        // Fallback info exists only if fallback is connected

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
        for (let i = 0; i < items.length; i++) {
            try {
                const primaryModelId = this.getNodeParameter('modelId', i) as string;
                const fallbackModelId = primaryModelId;
                // Get domain
                const domain = this.getNodeParameter('domain', i) as string;

                const intent = this.getNodeParameter('intention', i) as string;
                const context = this.getNodeParameter('context', i, '') as string;
                const status = this.getNodeParameter('status', i, '') as string;

                // Get categories (optional)
                const categoriesStr = this.getNodeParameter('categories', i) as string;
                let categoriesList: string[] = [];
                if (categoriesStr) {
                    categoriesList = categoriesStr.split(',').map((c: string) => c.trim());
                }

                const options = this.getNodeParameter('options', i) as IDataObject;

                let parsedStatus = {};
                try {
                    if (status) {
                        parsedStatus = typeof status === 'object' ? status : JSON.parse(status);
                    }
                } catch (e) {
                    parsedStatus = { raw: status };
                }

                const body: IDataObject = {
                    domain, // Add domain to request
                    intent,
                    context,
                    status: parsedStatus,
                    categories: categoriesList,
                };

                if (options.modelId) {
                    body.model_id = options.modelId;
                }
                if (options.systemPrompt) {
                    body.system_prompt = options.systemPrompt;
                }
                if (options.menuOptions) {
                    const menuData = (options.menuOptions as IDataObject).option as IDataObject[];
                    if (menuData) {
                        body.menu_options = menuData;
                    }
                }
                if (options.exceptions) {
                    const exceptionData = (options.exceptions as IDataObject).exception as IDataObject[];
                    if (exceptionData) {
                        body.exceptions = exceptionData;
                    }
                }


                const requestOptions: IHttpRequestOptions = {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    method: 'POST',
                    body,
                    json: true,
                    timeout: 60000,
                    url: `${baseUrl}/api/ai/sentiment/analyze`,
                };

                let response: any;
                let lastError: any;
                const maxRetries = 2;
                
                // Helper request
                const makeRequest = async (url: string, reqToken: string, reqBody: any) => {
                    let errOut: any;
                    for (let attempt = 0; attempt <= maxRetries; attempt++) {
                        try {
                            const reqOpt: IHttpRequestOptions = {
                                headers: {
                                    'Authorization': `Bearer ${reqToken}`,
                                    'Content-Type': 'application/json',
                                },
                                method: 'POST',
                                body: reqBody,
                                json: true,
                                timeout: 60000,
                                url,
                            };
                            return await this.helpers.httpRequest(reqOpt);
                        } catch (err: any) {
                            errOut = err;
                            if (attempt < maxRetries) {
                                await new Promise((resolve) => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                            }
                        }
                    }
                    throw errOut;
                };

                try {
                    response = await makeRequest(`${baseUrl}/api/ai/sentiment/analyze`, token, body);
                } catch (primaryError: any) {
                    if (fallbackBaseUrl && fallbackToken) {
                        try {
                            const fallbackBody = { ...body, model_id: fallbackModelId };
                            response = await makeRequest(`${fallbackBaseUrl}/api/ai/sentiment/analyze`, fallbackToken, fallbackBody);
                        } catch (fallbackError: any) {
                            const errorDetails = fallbackError.response?.data || fallbackError.response?.body || fallbackError.message;
                            throw new Error(`Both primary and fallback credentials failed. Fallback error: ${JSON.stringify(errorDetails)}`);
                        }
                    } else {
                        const errorDetails = primaryError.response?.data || primaryError.response?.body || primaryError.message;
                        throw new Error(`Primary request failed: ${JSON.stringify(errorDetails)}`);
                    }
                }

                const item = items[i];
                item.json = response;
                returnData.push(item);

            } catch (error) {
                if (this.continueOnFail()) {
                    items[i].json = { error: (error as any).message };
                    returnData.push(items[i]);
                    continue;
                }
                throw error;
            }
        }

        return this.prepareOutputData(returnData) as any;
    }
}
