import os
import logging
import tableauserverclient as TSC
from tableauserverclient import DatasourceItem


def datasource_to_string(datasource: DatasourceItem) -> str:
    """Returns a multi-line string containing a DatasourceItem's attributes"""
    return f"""
      name: {datasource.name}
      id: {datasource.id}
      content_url: {datasource.content_url}
      created_at: {datasource.created_at}
      certified: {datasource.certified}
      certification_note: {datasource.certification_note}
      datasource_type: {datasource.datasource_type}
      owner_id: {datasource.owner_id}
      project_id: {datasource.project_id}
      project_name: {datasource.project_name}
      tags: {datasource.tags}
      updated_at: {datasource.updated_at}
      """


class Publisher:
    """Publishes a Hyper file to a Tableau Server"""

    def __init__(self, tableau_server_url: str,
                 username: str, password: str,
                 site_id: str,
                 project_name: str,
                 datasource_name: str,
                 hyper_file_path: str):
        self.tableau_server_url = tableau_server_url
        self.username = username
        self.password = password
        self.site_id = site_id
        self.project_name = project_name
        self.project_id = None
        self.datasource_name = datasource_name
        self.datasource_luid = None
        self.hyper_file_path = hyper_file_path

    def publish(self, creation_mode='CreateNew'):
        """Publishes a Hyper File to a Tableau Server"""

        # Ensure that the Hyper File exists
        if not os.path.isfile(self.hyper_file_path):
            error = "{0}: Hyper File not found".format(self.hyper_file_path)
            raise IOError(error)

        # Check the Hyper File size
        hyper_file_size = os.path.getsize(self.hyper_file_path)
        logging.info(f"The Hyper File size is (in bytes): {hyper_file_size}")

        username_pw_auth = TSC.TableauAuth(username=self.username, password=self.password, site_id=self.site_id)
        server = TSC.Server(self.tableau_server_url)
        with server.auth.sign_in(username_pw_auth):

            # Search for project on the Tableau server
            projects, pagination = server.projects.get()
            for project in projects:
                if project.name == self.project_name:
                    logging.info(f'Found project on Tableau server. Project ID: {project.id}')
                    self.project_id = project.id

            # If project was not found on the Tableau Server, raise an error
            if self.project_id is None:
                raise ValueError(f'Invalid project name. Could not find project named "{self.project_name}" '
                                 f'on the Tableau server.')

            # Next, check if the datasource already exists and needs to be overwritten
            create_mode = TSC.Server.PublishMode.CreateNew
            if creation_mode.upper() == 'CREATENEW':
                datasources, pagination = server.datasources.get()
                for datasource in datasources:
                    # the datasource already exists, overwrite
                    if datasource.name == self.datasource_name:
                        logging.info(f'Overwriting existing datasource named "{self.datasource_name}".')
                        create_mode = TSC.Server.PublishMode.Overwrite
                        break
            elif creation_mode.upper() == 'APPEND':
                create_mode = TSC.Server.PublishMode.Append
            else:
                raise ValueError(f'Invalid "creation_mode" : {creation_mode}')

            # Finally, publish the Hyper File to the Tableau server
            logging.info(f'Publishing Hyper File located at: "{self.hyper_file_path}"')
            logging.info(f'Create mode: {create_mode}')
            datasource_item = TSC.DatasourceItem(project_id=self.project_id, name=self.datasource_name)
            logging.info(f'Publishing datasource: \n{datasource_to_string(datasource_item)}')
            datasource_item = server.datasources.publish(datasource_item=datasource_item,
                                                         file_path=self.hyper_file_path,
                                                         mode=create_mode)
            self.datasource_luid = datasource_item.id
            logging.info(f'Published datasource to Tableau server. Datasource LUID : {self.datasource_luid}')

        logging.info("Done.")

        return self.datasource_luid