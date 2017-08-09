#!/usr/bin/env node
import * as cp from "child_process";
import * as tfstate from "./lib/tfstate";
import * as fs from "fs";

var stateData;
var stateText = cp.spawnSync("terraform state pull", {shell: true}).stdout;

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
        this._hostvars.set(attrs.inventory_hostname, vars);
        this._groups["all"] = this._groups["all"] || [];
        this._groups["all"].push(attrs.inventory_hostname);
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
