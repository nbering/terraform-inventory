#!/usr/bin/env node
import * as cp from "child_process";
import * as tfstate from "./lib/tfstate";
import * as fs from "fs";

var terraformPath = process.env["TERRAFORM_PATH"] || "terraform10";

var stateData;
var stateText = cp.spawnSync(`${terraformPath} state pull`, {shell: true}).stdout;

try {
    stateData = JSON.parse(stateText.toString());
}
catch (e) {
    panic(e);
}

class AnsibleInventory{
    private _groups: {[key: string]: string[]} = {};
    private _hostvars = new Map<string, {[k:string]: any}>();

    addHost(attrs: tfstate.hostResourceAttrs){
        let vars = getMap("vars", attrs);
        let groups = getList("groups", attrs);
        let host = attrs.inventory_hostname;

        this._hostvars.set(host, vars);

        if (groups.indexOf("all") < 0)
            groups.push("all");

        groups.forEach(g => {
            this.appendToGroup(host, g);
        });
    }

    private appendToGroup(hostname: string, group: string){
        this._groups[group] = this._groups[group] || [];
        this._groups[group].push(hostname);
    }

    toString(): string{
        var out: any = Object.assign({}, this._groups);

        out._meta = {hostvars: {}};
        this._hostvars.forEach((value, key, map) => {
            out._meta.hostvars[key] = value;
        });

        return JSON.stringify(out, null, 4);
    }
}

var inventory = new AnsibleInventory();

walkState(stateData);

console.log(inventory.toString());

function panic(err: any){
    process.exit(1);
}

function getMap(key: string, source: {[key: string]: any}){
    let out: any = {};
    let filterExpression = new RegExp(`^${key}\.(.*)`);
    Object.keys(source)
        .filter(val => filterExpression.test(val))
        .map(val => {
            let match = val.match(filterExpression) || [];
            return match[1];
        })
        .forEach(subkey => {
            // Bail out terraform count field.
            if (subkey == "%")
                return;
            out[subkey] = source[`${key}.${subkey}`]
        });
    return out;
}

function getList(key: string, source: {[key: string]: any}){
    let out: any[] = [];
    let filterExpression = new RegExp(`^${key}\.(#|[0-9]+)$`);
    Object.keys(source)
        .filter(val => filterExpression.test(val))
        .map(val => {
            let match = val.match(filterExpression) || [];

            // If it's the count field, initilized
            if (match[1] === "#"){
                // This is a side-effect, which is to be avoided
                // with this type of functional compositiion...
                // but it makes this so much easier to write.
                out = new Array<any>(<number>source[val]);

                return -2;
            }

            // Conversion is a number, so return a number.
            return +match[1];
        })
        .forEach(index => {
            // Exit when flag is hit from count field.
            if (index === -2)
                return;

            if (!out)
                panic(new Error("List from state value did not have a count field."));

            out[index] = source[`${key}.${index}`];
        });

    return out || null;
}

function walkState(state: tfstate.tfstate){
    var module, rkey, res;
    for (module of state.modules){
        for (rkey in module.resources){
            res = module.resources[rkey];
            if(res.type != "ansible_host")
                continue;
            
            var attrs: tfstate.hostResourceAttrs = res.primary.attributes;
            inventory.addHost(attrs);
        }
    }
}
