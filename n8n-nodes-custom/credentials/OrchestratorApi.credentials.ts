import {
    ICredentialType,
    INodeProperties,
} from 'n8n-workflow';

export class OrchestratorApi implements ICredentialType {
    name = 'orchestratorApi';
    displayName = 'Orchestrator API';
    documentationUrl = 'https://qloryfy.com/n8n-docs';
    properties: INodeProperties[] = [
        {
            displayName: 'Base URL',
            name: 'baseUrl',
            type: 'string',
            default: 'https://qloryfy.com/api/',
        },
        {
            displayName: 'API Token',
            name: 'accessToken',
            type: 'string',
            typeOptions: {
                password: true,
            },
            default: '',
        },
    ];
}
