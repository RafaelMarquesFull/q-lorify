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
 * QlorifyCredentials - Sub-node (rounded) that supplies credential data
 * AND model ID to the Agent Formatter via the bottom "Credentials" port.
 *
 * The Model ID dropdown fetches only isOrchestrator-compatible models
 * from the API using the configured orchestratorApi credentials.
 */
export class QlorifyCredentials implements INodeType {
    description: INodeTypeDescription = {
        displayName: 'Qlorify: Credenciais',
        name: 'qlorifyCredentials',
        icon: 'file:icone.png',
        group: ['output'],
        version: 1,
        description: 'Provide API credentials and model selection to the Agent Formatter node',
        defaults: {
            name: 'Qlorify: Credenciais',
            color: '#6D28D9',
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
        // Output as ai_tool type (rendered as rounded sub-node)
        outputs: ['ai_tool' as any],
        outputNames: ['Credentials'],
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
                description: 'Select the AI model to use (only orchestrator-compatible models are shown)',
                required: true,
            },
            {
                displayName: 'Label',
                name: 'label',
                type: 'string',
                default: 'Primary',
                placeholder: 'Primary / Production...',
                description: 'A label to identify this credential set (e.g., "Primary")',
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
     * the credential data + model ID.
     */
    async supplyData(this: any): Promise<any> {
        const credentials = await this.getCredentials('orchestratorApi');

        if (!credentials) {
            throw new Error('No Agent credentials configured on this node');
        }

        const baseUrl = (credentials.baseUrl as string).replace(/\/$/, '');
        const accessToken = credentials.accessToken as string;
        const modelId = this.getNodeParameter('modelId', 0, '') as string;
        const label = this.getNodeParameter('label', 0, 'Primary') as string;
        const validateOnConnect = this.getNodeParameter('validateOnConnect', 0, false) as boolean;

        // Optional validation
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
                    `Agent credential validation failed [${label}]: ${error.message}. ` +
                    `Check if Base URL "${baseUrl}" is correct.`
                );
            }
        }

        // Return credentials + model ID for the parent node to consume
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
