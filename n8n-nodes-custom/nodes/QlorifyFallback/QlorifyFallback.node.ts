import {
    INodeType,
    INodeTypeDescription,
    INodePropertyOptions,
    ILoadOptionsFunctions,
} from 'n8n-workflow';

import {
    OptionsWithUri,
} from 'request';

/**
 * QlorifyFallback - Sub-node (rounded) that supplies FALLBACK credential data
 * AND model ID to the Agent Formatter via the bottom "Fallback" port.
 *
 * Identical to QlorifyCredentials but outputs 'ai_languageModel' type
 * so it connects to the dedicated Fallback port (separate from Credentials port).
 *
 * Only shows isOrchestrator-compatible models in the dropdown.
 * Used when the primary credentials fail — the Formatter automatically retries
 * with these fallback credentials + model.
 */
export class QlorifyFallback implements INodeType {
    description: INodeTypeDescription = {
        displayName: 'Qlorify: Fallback',
        name: 'qlorifyFallback',
        icon: 'file:icone.png',
        group: ['output'],
        version: 1,
        description: 'Provide fallback API credentials and model — used when primary credentials fail',
        defaults: {
            name: 'Qlorify: Fallback',
            color: '#DC2626',
        },
        codex: {
            categories: ['AI'],
            subcategories: {
                AI: ['Tools'],
                Tools: ['Other Tools'],
            },
        },
        // Sub-node: no main input
        inputs: [],
        // Output as ai_languageModel type (renders as rounded sub-node on separate port)
        outputs: ['ai_languageModel' as any],
        outputNames: ['Fallback'],
        credentials: [
            {
                name: 'orchestratorApi',
                required: true,
            },
        ],
        properties: [
            {
                displayName: 'Model ID',
                name: 'modelId',
                type: 'options',
                typeOptions: {
                    loadOptionsMethod: 'getModels',
                },
                default: '',
                description: 'Select the AI model to use for fallback (only orchestrator-compatible models are shown)',
                required: true,
            },
            {
                displayName: 'Label',
                name: 'label',
                type: 'string',
                default: 'Fallback',
                placeholder: 'Fallback / Backup / Staging...',
                description: 'A label to identify this fallback credential set',
            },
            {
                displayName: 'Validate on Connect',
                name: 'validateOnConnect',
                type: 'boolean',
                default: false,
                description: 'Whether to validate credentials by pinging the API when the workflow executes',
            },
        ],
    };

    methods = {
        loadOptions: {
            async getModels(this: ILoadOptionsFunctions): Promise<INodePropertyOptions[]> {
                const returnData: INodePropertyOptions[] = [];

                try {
                    const credentials = await this.getCredentials('orchestratorApi');
                    if (credentials) {
                        const baseUrl = (credentials.baseUrl as string).replace(/\/$/, '');

                        const options: OptionsWithUri = {
                            method: 'GET',
                            uri: `${baseUrl}/api/public/models`,
                            json: true,
                        };

                        const response = await this.helpers.request(options);

                        if (Array.isArray(response)) {
                            for (const model of response) {
                                // Only show isOrchestrator-compatible models
                                if (model.isOrchestrator) {
                                    returnData.push({
                                        name: `${model.name} (${model.provider || 'Agent'})`,
                                        value: model.id,
                                    });
                                }
                            }
                        }
                    }
                } catch (error: any) {
                    throw new Error(`Failed to load models: ${error.message}`);
                }

                return returnData;
            },
        },
    } as any;

    /**
     * supplyData - Called by the parent node (Agent Formatter) to get
     * the fallback credential data + model ID.
     */
    async supplyData(this: any): Promise<any> {
        const credentials = await this.getCredentials('orchestratorApi');

        if (!credentials) {
            throw new Error('No Agent fallback credentials configured on this node');
        }

        const baseUrl = (credentials.baseUrl as string).replace(/\/$/, '');
        const accessToken = credentials.accessToken as string;
        const modelId = this.getNodeParameter('modelId', 0, '') as string;
        const label = this.getNodeParameter('label', 0, 'Fallback') as string;
        const validateOnConnect = this.getNodeParameter('validateOnConnect', 0, false) as boolean;

        if (validateOnConnect) {
            try {
                const options: OptionsWithUri = {
                    method: 'GET',
                    uri: `${baseUrl}/api/public/models`,
                    json: true,
                    timeout: 10000,
                };
                await this.helpers.request(options);
            } catch (error: any) {
                throw new Error(
                    `Agent fallback credential validation failed [${label}]: ${error.message}. ` +
                    `Check if Base URL "${baseUrl}" is correct.`
                );
            }
        }

        return {
            response: {
                baseUrl,
                accessToken,
                modelId,
                label,
            },
        };
    }
}
