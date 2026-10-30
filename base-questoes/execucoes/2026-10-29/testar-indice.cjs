const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('base-questoes/dados/index.html','utf8');
const data=html.match(/<script type="application\/json" id="dados">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element {constructor(){this.textContent='';this.value='';this.children=[];this.events={}}append(...nodes){this.children.push(...nodes)}replaceChildren(...nodes){this.children=nodes}addEventListener(name,fn){this.events[name]=fn}}
const nodes=new Map();const document={getElementById(id){if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id)},createElement(){return new Element()}};
document.getElementById('dados').textContent=data;
vm.runInNewContext(script,{document});
assert.equal(nodes.get('resultados').children.length,25);assert.equal(nodes.get('contador').textContent,JSON.parse(data).length+' resultados');
nodes.get('busca').value='restos a pagar';nodes.get('busca').events.input();assert(nodes.get('resultados').children.length>0);
nodes.get('busca').value='"restos a pagar"';nodes.get('busca').events.input();assert(nodes.get('resultados').children.length>0);
nodes.get('tipo').value='Tópico';nodes.get('tipo').events.input();assert(nodes.get('resultados').children.length>0);
nodes.get('busca').value='zzzxxyysemresultado';nodes.get('busca').events.input();assert.equal(nodes.get('resultados').children.length,0);
console.log('Índice: inicialização, busca, filtro e ausência de resultados passaram.');
