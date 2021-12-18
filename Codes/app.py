from flask import Flask, render_template, request, redirect
from neo4j import GraphDatabase
from urllib.request import urlopen
import json

#Neo4J database credentials
uri             = "bolt://localhost:7687"
userName        = "neo4j"
password        = "movie"

#OMDB API Key
api_key = '4ac78a08'

app = Flask(__name__)

graphDB_Driver  = GraphDatabase.driver(uri, auth=(userName, password))

@app.route('/', methods = ["GET"])
def index():
    cql = "MATCH (x:Genre) RETURN x.genre AS genre"
    with graphDB_Driver.session() as graphDB_Session:
        nodes = graphDB_Session.run(cql)
        nodeList = []
        for node in nodes:
            nodeList.append(node.data()['genre'])
    return render_template('index.html', labels = nodeList)

@app.route('/', methods = ["POST"])
def showMovies():
    genreList = request.form.getlist('genre')
    query = "MATCH (m:Movie)-[HAS_GENRE]->(g:Genre) WHERE g.genre = $genre RETURN m.imdbTitle AS imdb_id ORDER BY m.rating DESC LIMIT 5"
    movieList = []
    with graphDB_Driver.session() as graphDB_Session:
        for gnr in genreList:
            movies = graphDB_Session.run(query, genre = gnr)
            for movie in movies:
                movieList.append(movie.data()["imdb_id"])

    omdb_request_url = 'http://www.omdbapi.com/?apikey=' + api_key + '&i='

    movie_dict = {}
    for movie in movieList:
        json_request_url = omdb_request_url + movie
        response = urlopen(json_request_url)
        json_dict = json.loads(response.read())
        movie_dict[movie] = [json_dict['Title'], json_dict['Poster']]

    return render_template('movies.html', movies = movie_dict)

@app.route('/movies', methods = ["POST"])
def recommendMovies():
    query1 = "MATCH (m:Movie)-[HAS_GENRE]->(g:Genre) WHERE m.imdbTitle = $imdb_id RETURN g.genre AS genre"
    query2 = "MATCH (m:Movie)-[HAS_GENRE]->(g:Genre) WHERE m.imdbTitle = $imdb_id RETURN m.year AS year, m.duration AS duration, m.rating AS rating"
    movieList = request.form.getlist('watch')
    recommendations = []
    genre_dict = {}
    movie_data_dict = {}
    with graphDB_Driver.session() as graphDB_Session:
        for movie in movieList:
            genres = graphDB_Session.run(query1, imdb_id = movie)
            genreList = []
            for genre in genres:
                genreList.append(genre.data()["genre"])
            genre_dict[movie] = genreList

            movie_data = graphDB_Session.run(query2, imdb_id = movie)
            for data in movie_data:
                movie_data_dict[movie] = [int(data.data()["year"]), int(data.data()["duration"]), float(data.data()["rating"])]

    query3 = "MATCH (m:Movie)-[HAS_GENRE]->(g:Genre) WHERE toInteger(m.year) <= $rightyear AND toInteger(m.year) >= $leftyear AND toInteger(m.duration) >= $leftdur AND toInteger(m.duration) <= $rightdur AND toFloat(m.rating) >= $leftrtng AND toFloat(m.rating) <= $rightrtng AND g.genre IN $genre_list RETURN DISTINCT m.imdbTitle AS imdb_id LIMIT 10"
    with graphDB_Driver.session() as graphDB_Session:
        for movie in movieList:
            year = movie_data_dict[movie][0]
            duration = movie_data_dict[movie][1]
            rating = movie_data_dict[movie][2]
            genres = genre_dict[movie]
            if year > 2000:
                ly = year - 5
                ry = year + 5
            else:
                ly = year - 10
                ry = year + 10

            ld = duration - 30
            rd = duration + 30
            lr = rating - 2.5
            rr = rating + 2.5
            data = graphDB_Session.run(query3, leftyear = ly, rightyear = ry, leftdur = ld, rightdur = rd, leftrtng = lr, rightrtng = rr, genre_list = genres)
            for d in data:
                recommendations.append(d.data()['imdb_id'])

    omdb_request_url = 'http://www.omdbapi.com/?apikey=' + api_key + '&i='

    movie_dict = {}
    for movie in recommendations:
        json_request_url = omdb_request_url + movie
        response = urlopen(json_request_url)
        json_dict = json.loads(response.read())
        movie_dict[movie] = [json_dict['Title'], json_dict['Poster']]

    return render_template('movies.html', movies = movie_dict)

@app.route('/search', methods = ["POST"])
def searchMovie():
    search = request.form.get('searchbar')
    query = "MATCH (m:Movie) WHERE toLower(m.title) CONTAINS toLower($search_request) RETURN m.imdbTitle AS imdb_id ORDER BY m.rating DESC LIMIT 10"
    movieList = []
    with graphDB_Driver.session() as graphDB_Session:
        movies = graphDB_Session.run(query, search_request = search)
        for movie in movies:
            movieList.append(movie.data()["imdb_id"])

    omdb_request_url = 'http://www.omdbapi.com/?apikey=' + api_key + '&i='

    movie_dict = {}
    for movie in movieList:
        json_request_url = omdb_request_url + movie
        response = urlopen(json_request_url)
        json_dict = json.loads(response.read())
        movie_dict[movie] = [json_dict['Title'], json_dict['Poster']]

    return render_template('movies.html', movies = movie_dict)

if __name__ == "__main__":
    app.run(debug = True)
