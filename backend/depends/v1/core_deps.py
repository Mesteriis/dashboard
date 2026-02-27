from __future__ import annotations

from typing import Annotated

from config.container import AppContainer
from core.bus import BrokerActionRPC
from core.config import ConfigService
from core.gateway import ActionGateway
from core.storage.repositories import ActionRepository
from depends.v1.deps import get_container
from fastapi import Depends

ContainerDep = Annotated[AppContainer, Depends(get_container)]


def get_config_service(container: ContainerDep) -> ConfigService:
    return container.config_service


def get_event_bus(container: ContainerDep):
    return container.event_bus


def get_gateway(container: ContainerDep) -> ActionGateway:
    return container.gateway


def get_action_repository(container: ContainerDep) -> ActionRepository:
    return container.action_repository


def get_action_rpc_client(container: ContainerDep) -> BrokerActionRPC:
    return container.action_rpc_client


ConfigServiceDep = Annotated[ConfigService, Depends(get_config_service)]
GatewayDep = Annotated[ActionGateway, Depends(get_gateway)]
ActionRepositoryDep = Annotated[ActionRepository, Depends(get_action_repository)]
ActionRpcClientDep = Annotated[BrokerActionRPC, Depends(get_action_rpc_client)]


__all__ = [
    "ActionRepositoryDep",
    "ActionRpcClientDep",
    "ConfigServiceDep",
    "ContainerDep",
    "GatewayDep",
    "get_action_repository",
    "get_action_rpc_client",
    "get_config_service",
    "get_event_bus",
    "get_gateway",
]
