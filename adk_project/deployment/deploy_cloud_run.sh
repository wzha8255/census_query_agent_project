adk deploy cloud_run \
--project=$GOOGLE_CLOUD_PROJECT \
--region=$GOOGLE_CLOUD_LOCATION \
--service_name=$SERVICE_NAME \
--app_name=$APP_NAME \
--with_ui \
./census_query_agent




adk deploy cloud_run  \
--service-account SERVICE_ACCOUNT_ADDRESS \
--project PROJECT_ID --region REGION 
