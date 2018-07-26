# NII internship 2018

Research project for 2017 2nd Call NII International Internship.
Main target: Social Network of seiyuu (anime voice actors) analysis.

## Folders
* Code: contains scripts used for getting information, making graphs and run predictions.
* Data: json and rdf data backup, may be outdated.
* Graphics: backup of graphics.
* PopularityPredictionResults: results backup for an execution of "popularity predictions" script.
* Presentation: latex files for presentation.
* Report: latex files for report.
* SocialNetworks: backup of some of the social networks built.

## Steps to get RDF data
1. Get list of seiyuu from Wikidata.
   * Using: retrieveSeiyuuListFromWikidata.py 
   * Parameters: name of output file, limit

2. Get seiyuu info and store it locally using mongodb in order to not depend on API limit.
   * Using: getSeiyuuInfo.py 
   * Parameters: input file name, output file name, from seiyuu index, to seiyuu index, limit to x api consults
     > Input file is the output from point 1

3. Convert seiyuu information to RDF-turtle and store it locally using virtuoso.
   * Using: seiyuuInfoToRDF.py
   * parameters: input file name, output file name

4. Get anime info and store it locally using mongodb in order to not depend on API limit.
   * Using: getAnimeInfo.py
   * Parameters: input file name, output file name, from anime index, to anime index, limit to x api consults
     > Input file is actually a list of anime uris (jikan API page) this can be obtained by querying virtuoso server
    
5. Convert anime information to RDF-turtle and store it locally using virtuoso.
   * Using: animeInfoToRDF.py
   * Parameters: input file name, output file name

6. There are a couple of scripts that recover certain information, such as debut or personal data. This can be separately and added to local database if needed.
