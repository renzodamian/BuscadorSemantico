from django.shortcuts import render
from django.views.generic import TemplateView
from .forms import *
import spacy
from spacy import displacy
import es_core_news_sm
import rdflib
from rdflib.serializer import Serializer
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import OrderedDict
import itertools
import re
from unicodedata import normalize

# clase que renderiza la plantilla
class InicioView(TemplateView):
    plantilla = 'buscador/index.html'
    formulario = BuscadorForm()

    def get(self, request):
        args = {"formulario": self.formulario}
        return render(request, self.plantilla, args)

    def post(self, request):
        formulario = BuscadorForm(request.POST)
        if formulario.is_valid():
            text = formulario.cleaned_data['query']
            texto_inicial = text
            # llama clase
            token = Semantico()
            datos, ent, spacyText,datostype,datoscompani= token.consultaVirutoso(text)
            texto_inicial = token.textoHtml(text, ent)
            # elimina datos dupliados de lista
            datos = OrderedDict((tuple(x), x) for x in datos).values()
            args = {"datos": datos, "formulario": self.formulario, "texto_inicial": texto_inicial,"spacyText":spacyText,"datatype":datostype,"datacompani":datoscompani}
        return render(request, self.plantilla, args)


#class Detalles(TemplateView):
#    plantilla = 'buscador/detalles.html'
#    def get(self, request, id):
#        response = id
#        uri = 'http://data.utpl.edu.ec/casoav/resources/'
#        uri = uri+response
#        token = Semantico()
#        datos = token.obtenerRecursos(uri)
#        args = {"datos": datos}
#        return render(request, self.plantilla,args)

class Semantico():
    # sparql endopoint
    sbcEndpoint = SPARQLWrapper("http://localhost:8890/sparql/")
    nlp = es_core_news_sm.load()
    #g = rdflib.Graph()
    #g.parse("datos.rdf")

    def consultaVirutoso(self, texto):
        # tokenizar texto con spacy
        text = self.nlp(texto)
        tokenized_sentences = [sentence.text for sentence in text.sents]
        # dar estilos al texo analizado
        spacyText = displacy.render(text, style="ent")
        # declaras listas vacias
        datos = []
        datostype = []
        datoscompani = []
        entidades = []
        for sentence in tokenized_sentences:
            for entity in self.nlp(sentence).ents:
                entidades.append(entity.text)
                palabra = self.limpiarDatos(entity)
                consulta = """
                SELECT ?s ?p ?o
                    WHERE 
                        { 
                            ?s ?p ?o .FILTER (regex(str(?s), "%s") || regex(str(?o), "%s")) .
                        }
                        """ % (palabra,palabra)
                self.sbcEndpoint.setQuery(consulta)
                # retornar consulta enformto json
                self.sbcEndpoint.setReturnFormat(JSON)
                results = self.sbcEndpoint.query().convert()
                for result in results["results"]["bindings"]:
                    lista = []
                    listaS = result["s"]["value"]
                    listaP = result["p"]["value"]
                    listaO = result["o"]["value"]
                    lista.append(listaS)
                    lista.append(listaP)
                    lista.append(listaO)
                    datos.append(lista)
        for sentence in tokenized_sentences:
            for entity in self.nlp(sentence).ents:
                entidades.append(entity.text)
                palabra = self.limpiarDatos(entity)
                consultatype = """
                PREFIX caseav: <http://localhost:8080/Data/page/>
                SELECT ?o
                    WHERE 
                        { 
                           {?s  caseav:hasNombrePersona ?o .FILTER (regex(str(?o), "%s")) .}  
                           UNION
                           {?s caseav:hashasApellidoPersona ?o .FILTER (regex(str(?o), "%s")) .}
                           UNION
                           {?s  caseav:hasCodigo ?o .FILTER (regex(Str(?o), "%s")) .} 
                           UNION
                           {?s  caseav:hasNombreCompletoPersona ?o .FILTER (regex(Str(?o), "%s")) .} 
                        }
                        """ % (palabra,palabra,palabra,palabra)
                self.sbcEndpoint.setQuery(consultatype)
                # retornar consulta enformto json
                self.sbcEndpoint.setReturnFormat(JSON)
                results = self.sbcEndpoint.query().convert()
                for result in results["results"]["bindings"]:
                    listae = []
                    #listaSe = result["s"]["value"]
                    #listaPe = result["p"]["value"]
                    listaOe = result["o"]["value"]
                    #listae.append(listaSe)
                    #listae.append(listaPe)
                    listae.append(listaOe)
                    datostype.append(listae)
        for sentence in tokenized_sentences:
            for entity in self.nlp(sentence).ents:
                entidades.append(entity.text)
                palabra = self.limpiarDatos(entity)
                consultacompani = """
                PREFIX caseav: <http://localhost:8080/Data/page/>
                SELECT ?s ?o
                    WHERE 
                        { 
                           {?s  caseav:hasNombreEmpresa  ?o .FILTER (regex(str(?o), "%s")) .}
                        }
                        """ % (palabra)
                self.sbcEndpoint.setQuery(consultacompani)
                # retornar consulta enformto json
                self.sbcEndpoint.setReturnFormat(JSON)
                results = self.sbcEndpoint.query().convert()
                for result in results["results"]["bindings"]:
                    
                    listaec = []
                    #listaSe = result["s"]["value"]
                    #listaPe = result["p"]["value"]
                    listaOec = result["o"]["value"]
                    #listae.append(listaSe)
                    #listae.append(listaPe)
                    listaec.append(listaOec)
                    datoscompani.append(listaec)
        return datos, entidades, spacyText,datostype,datoscompani
        
    def textoHtml(self, texto, entidades):
        for palabra in entidades:
            if palabra in texto:
                # reemplazo de tildes
                # -> NFD y eliminar diacríticos
                s = re.sub(
                        r"([^n\u0300-\u036f]|n(?!\u0303(?![\u0300-\u036f])))[\u0300-\u036f]+", r"\1", 
                        normalize( "NFD", palabra), 0, re.I
                    )

                # -> NFC
                s = normalize( 'NFC', s)
                palabraUrl = s.replace(" ","_")
                palabraUrl = self.limpiarDatos(palabraUrl)
                url = '<a href = "http://localhost:8080/Data/page/{}">{}</a>'.format(palabraUrl,palabra)
                if url not in texto:
                    texto = texto.replace(palabra, url)
        return texto


    def limpiarDatos(self,palabra):
        palabra = str(palabra)
        palabra = palabra.replace(' ','_')
        palabra = palabra.replace('á','a')
        palabra = palabra.replace('é','e')
        palabra = palabra.replace('í','i')
        palabra = palabra.replace('ó','o')
        palabra = palabra.replace('ú','u')
        palabra = palabra.replace('Alianza_Pais','AP')
        palabra = palabra.replace('Alianza_PAIS','AP')
        palabra = palabra.replace('Hidalgo_&_Hidalgo','HIDALGO_&_HIDALGO')
        palabra = palabra.replace('Fopeca','FOPECA')
        palabra = palabra.replace('Midisa_S.A','MIDISA_S.A')
        palabra = palabra.replace('Pamela_Martinez','Maria_Pamela_Martinez_Loaiza')
        return palabra