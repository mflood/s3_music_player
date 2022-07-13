


drop table book_tag;
drop table book;

create table book_tag (
    book_tag_id INTEGER PRIMARY KEY AUTOINCREMENT ,
    name text unique);


insert into book_tag (name) values ("korean");
insert into book_tag (name) values ("mind");
insert into book_tag (name) values ("game development");

create table book (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title text);

insert into book (title) values ("A Game Design Vocabulary");

create table book_join_book_tab (
    book_id INTEGER,
    book_tag_id INTEGER,
    primary key (book_id, book_tag_id)
    );

insert into book_join_book_tab (book_id, book_tag_id) values (1, 3);

