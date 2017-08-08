export interface tfstate{
    version: number,
    terraform_version: string,
    serial: number,
    lineage: string,
    modules: tfstateModule[]
}

export interface tfstateModule{
    path: string[],
    outputs: {
        [key: string]: tfstateModuleOutput
    },
    resources: {
        [k: string]: tfstateResource
    }
}

export interface tfstateModuleOutput{
    sensitive: boolean,
    type: string,
    value: any
}

export interface tfstateResource{
    type: string,
    depends_on: string[],
    primary: tfstateResourceData,
    deposed: any[],
    provider: string
}

export interface hostResourceAttrs{
    inventory_hostname: string,
    vars: {
        [key: string]: any
    }
}

export interface tfstateResourceData{
    id: string,
    attributes: any,
    meta: {
        schema_version: string
    },
    tainted: boolean
}
