

set search_path='music';
drop table if exists music.test_table;
drop table if exists music.profile;
drop schema if exists music;
create schema music;


create table music.song (
    song_id serial not null primary key,
    title text not null
);


insert into song (title) values ('test');
insert into song (title) values ('test');
insert into song (title) values ('test');
select * from song;


create table music.profile(

    profile_id serial not null primary key,
    profile_name text not null unique
);

insert into profile (profile_name) values ('matt one');
insert into profile (profile_name) values ('matt two');
select * from profile;


create table music.deck (
    deck_id serial not null primary_key,
    parent_deck_id seria defualt null,
    profile_id serial not null,
    name text not null);

insert into music.deck (profile_id, name) values (1, 'vitamin');
insert into music.deck (profile_id, name) values (1, 'integrated');
insert into music.deck (profile_id, name) values (1, '');

