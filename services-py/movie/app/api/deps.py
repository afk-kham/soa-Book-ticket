"""Dependency Injection cho Movie Service."""
from fastapi import Depends

from app.controllers.movie_controller import MovieController
from app.repositories.movie_repository import MovieRepository
from app.services.movie_service import MovieService


def get_movie_repository() -> MovieRepository:
    return MovieRepository()


def get_movie_service(repo: MovieRepository = Depends(get_movie_repository)) -> MovieService:
    return MovieService(repo)


def get_movie_controller(service: MovieService = Depends(get_movie_service)) -> MovieController:
    return MovieController(service)

