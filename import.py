""" Universidad Yachay Tech
Diego Hernán Suntaxi Domínguez
Curso de Web Programming
Prof. Rigoberto Fonseca  
 """
import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year) ON CONFLICT (isbn) DO UPDATE SET title = excluded.title, author = excluded.author, year = excluded.year;", {"isbn": isbn, "title":title, "author": author, "year": year})
            # print(f"Added flight from {origin} to {destination} lasting {duration} minutes.")
    db.commit()

if __name__ == "__main__":
    main()

""" 
    INSERT INTO the_table (id, column_1, column_2) 
VALUES (1, 'A', 'X'), (2, 'B', 'Y'), (3, 'C', 'Z')
ON CONFLICT (id) DO UPDATE 
  SET column_1 = excluded.column_1, 
      column_2 = excluded.column_2;
       """