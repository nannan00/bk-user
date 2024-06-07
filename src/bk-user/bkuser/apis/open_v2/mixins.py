# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-用户管理(Bk-User) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from functools import cached_property
from typing import Dict, Tuple

from django.db.models import Q, QuerySet
from rest_framework.permissions import IsAuthenticated

from bkuser.apis.open_v2.authentications import ESBAuthentication
from bkuser.apis.open_v2.renderers import BkLegacyApiJSONRenderer
from bkuser.apps.data_source.constants import DataSourceTypeEnum
from bkuser.apps.data_source.models import DataSource
from bkuser.apps.tenant.constants import CollaborationStrategyStatus
from bkuser.apps.tenant.models import CollaborationStrategy, Tenant


class LegacyOpenApiCommonMixin:
    authentication_classes = [ESBAuthentication]
    permission_classes = [IsAuthenticated]
    renderer_classes = [BkLegacyApiJSONRenderer]


class DefaultTenantMixin:
    """默认租户 Mixin"""

    @cached_property
    def default_tenant(self) -> Tenant:
        return Tenant.objects.filter(is_default=True).first()

    def get_real_user_data_source(self) -> QuerySet[DataSource]:
        """获取默认租户真实用户数据源（含自己的 + 协同过来的），兼容 V2 的 OpenAPI 专用"""
        # 接受方确认过的数据源，就是认为是有数据的
        collaboration_tenant_ids = (
            CollaborationStrategy.objects.filter(target_tenant=self.default_tenant)
            .exclude(target_status=CollaborationStrategyStatus.UNCONFIRMED)
            .values_list("source_tenant_id", flat=True)
        )
        return DataSource.objects.filter(
            Q(owner_tenant_id=self.default_tenant.id) | Q(owner_tenant_id__in=collaboration_tenant_ids)
        ).filter(type=DataSourceTypeEnum.REAL)

    def get_collaboration_field_mapping(self) -> Dict[Tuple[str, str], str]:
        """
        默认租户的所有协同租户字段映射

        :return: {(collaboration_tenant_id, source_field): target_field}
        """
        strategies = CollaborationStrategy.objects.filter(target_tenant_id=self.default_tenant.id)

        return {
            (strategy.source_tenant_id, mp["source_field"]): mp["target_field"]
            for strategy in strategies
            for mp in strategy.target_config["field_mapping"]
        }


class DataSourceOwnerTenantMixin:
    """数据源 Owner 租户相关"""

    @cached_property
    def data_source_owner_tenant_id_map(self) -> Dict[int, str]:
        return dict(ds.id for ds in DataSource.objects.values_list("id", "owner_tenant_id"))

    def get_data_source_owner_tenant_id(self, data_source_id: int) -> str:
        return self.data_source_owner_tenant_id_map[data_source_id]
