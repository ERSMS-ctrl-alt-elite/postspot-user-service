# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# TODO (https://github.com/GoogleCloudPlatform/python-docs-samples/issues/8253): remove old region tags
# [START cloud_sql_mysql_sqlalchemy_connect_tcp]
# [START cloud_sql_mysql_sqlalchemy_sslcerts]
# [START cloud_sql_mysql_sqlalchemy_connect_tcp_sslcerts]
import os

import sqlalchemy
from sqlalchemy import text


def connect_tcp_socket() -> sqlalchemy.engine.base.Engine:
    """Initializes a TCP connection pool for a Cloud SQL instance of MySQL."""
    # Note: Saving credentials in environment variables is convenient, but not
    # secure - consider a more secure solution such as
    # Cloud Secret Manager (https://cloud.google.com/secret-manager) to help
    # keep secrets safe.
    db_host = "34.116.166.68"
    db_user = "postspot"
    db_pass = "<Po~.igsUFAlYAx"
    db_name = "test-instance"
    db_port = 3306

    # [END cloud_sql_mysql_sqlalchemy_connect_tcp]
    connect_args = {}
    # For deployments that connect directly to a Cloud SQL instance without
    # using the Cloud SQL Proxy, configuring SSL certificates will ensure the
    # connection is encrypted.
    if os.environ.get("DB_ROOT_CERT"):
        db_root_cert = os.environ["DB_ROOT_CERT"]  # e.g. '/path/to/my/server-ca.pem'
        db_cert = os.environ["DB_CERT"]  # e.g. '/path/to/my/client-cert.pem'
        db_key = os.environ["DB_KEY"]  # e.g. '/path/to/my/client-key.pem'

        ssl_args = {"ssl_ca": db_root_cert, "ssl_cert": db_cert, "ssl_key": db_key}
        connect_args = ssl_args

    # [START cloud_sql_mysql_sqlalchemy_connect_tcp]
    pool = sqlalchemy.create_engine(
        # Equivalent URL:
        # mysql+pymysql://<db_user>:<db_pass>@<db_host>:<db_port>/<db_name>
        sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
            username=db_user,
            password=db_pass,
            host=db_host,
            port=db_port,
            database=db_name,
        ),
        # [END cloud_sql_mysql_sqlalchemy_connect_tcp]
        connect_args=connect_args,
        # [START cloud_sql_mysql_sqlalchemy_connect_tcp]
        # [START_EXCLUDE]
        # [START cloud_sql_mysql_sqlalchemy_limit]
        # Pool size is the maximum number of permanent connections to keep.
        pool_size=5,
        # Temporarily exceeds the set pool_size if no connections are available.
        max_overflow=2,
        # The total number of concurrent connections for your application will be
        # a total of pool_size and max_overflow.
        # [END cloud_sql_mysql_sqlalchemy_limit]
        # [START cloud_sql_mysql_sqlalchemy_backoff]
        # SQLAlchemy automatically uses delays between failed connection attempts,
        # but provides no arguments for configuration.
        # [END cloud_sql_mysql_sqlalchemy_backoff]
        # [START cloud_sql_mysql_sqlalchemy_timeout]
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        pool_timeout=30,  # 30 seconds
        # [END cloud_sql_mysql_sqlalchemy_timeout]
        # [START cloud_sql_mysql_sqlalchemy_lifetime]
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # re-established
        pool_recycle=1800,  # 30 minutes
        # [END cloud_sql_mysql_sqlalchemy_lifetime]
        # [END_EXCLUDE]
    )
    return pool


# [END cloud_sql_mysql_sqlalchemy_connect_tcp_sslcerts]
# [END cloud_sql_mysql_sqlalchemy_sslcerts]
# [END cloud_sql_mysql_sqlalchemy_connect_tcp]

pool = connect_tcp_socket()
print("Connecting to MySQL database")
with pool.connect() as connection:
    print("Successfully connected to MySQL databaser")
    print("Executing select from * user")
    result = connection.execute(text("select * from user"))
    print(f"{result=}")
