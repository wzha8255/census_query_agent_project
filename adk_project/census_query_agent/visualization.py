from io import BytesIO
import base64
import datetime
import uuid
from typing import List, Dict, Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
# for the function to upload files to gcs bucket
from google.cloud import storage


class VisualizationTool:
    """Simple visualization helper that converts query results (list of dicts)
    or pandas DataFrame into a PNG image (base64-encoded) for quick client display.

    Usage:
      - Call `plot_from_rows(rows, x, y, kind='bar')` where `rows` is a list of
        dict-like records returned from BigQuery tool.
      - Or call `plot_from_dataframe(df, ...)` directly with a pandas DataFrame.

    Returns a dictionary with keys:
      - 'png_base64': base64-encoded PNG bytes (no data URI prefix)
      - 'data_uri': a ``data:image/png;base64,...`` string suitable for embedding in HTML
      - 'width' and 'height' in inches for reference
    """

    def __init__(self):
        # default seaborn style
        sns.set_style('whitegrid')

    def _df_from_rows(self, rows: List[Dict]) -> pd.DataFrame:
        # Convert list of dict records to DataFrame
        return pd.DataFrame(rows)

    def plot_from_rows(
        self,
        rows: List[Dict],
        x: str,
        y: str,
        kind: str = 'bar',
        title: Optional[str] = None,
        top_n: Optional[int] = None,
        figsize=(8, 4),
        rotate_xticks: bool = True,
    ) -> Dict:
        # convert list of dictionary python objects to a pandas dataframe object
        df = self._df_from_rows(rows)
        ## call the other function to plot using a pandas dataframe object
        return self.plot_from_dataframe(df, x=x, y=y, kind=kind, title=title, top_n=top_n, figsize=figsize, rotate_xticks=rotate_xticks)


    ## this is the key function for the whole class, generate a visual using a given pandas dataframe
    def plot_from_dataframe(
        self,
        df: pd.DataFrame,
        x: str,
        y: str,
        kind: str = 'bar',
        title: Optional[str] = None, ## Optional[str] = Union[str, None]
        top_n: Optional[int] = None,  ## Optional[int] = Union[int, None]
        figsize=(8, 4),
        rotate_xticks: bool = True,
    ) -> Dict:
        
        
        if top_n is not None and x in df.columns:
            df = df.nlargest(top_n, y)

        # Basic plotting support: bar, line, scatter
        plt.close('all')
        fig, ax = plt.subplots(figsize=figsize)

        if kind == 'bar':
            sns.barplot(data=df, x=x, y=y, ax=ax, palette='viridis')
        elif kind == 'line':
            sns.lineplot(data=df, x=x, y=y, ax=ax)
        elif kind == 'scatter':
            sns.scatterplot(data=df, x=x, y=y, ax=ax)
        else:
            # fallback to bar
            sns.barplot(data=df, x=x, y=y, ax=ax)

        if title:
            ax.set_title(title)
        if rotate_xticks:
            plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        png_bytes = buf.getvalue()
        png_b64 = base64.b64encode(png_bytes).decode('ascii') ## a binary image converted to text using Base64 encoding, basically its a text which represents an image
        data_uri = f"data:image/png;base64,{png_b64}"

        return {
            'png_base64': png_b64,
            'data_uri': data_uri,
            'width': figsize[0],
            'height': figsize[1],
            'format': 'png',
        }

    # convenience: accept BigQuery tool results that may include typed values
    def plot_from_bq_result(self, bq_result: List[Dict], x: str, y: str, **kwargs) -> Dict:
        # The BigQuery tool often returns rows as dicts already; attempt to normalize
        return self.plot_from_rows(bq_result, x=x, y=y, **kwargs)


    ## difference between bucket name and blob name::
    ## bucket name: the globally unique identifier for an object bucket on gcp cloud
    ## as there is no file system in gcs bucket, its a object storage. however, hierarchy blob name can simulate a 
    ## file system functions like folders subfolders and files.
    def upload_to_gcs(
        self,
        png_base64: str,
        bucket_name: str,
        blob_name: Optional[str] = None,
        expiration_minutes: int = 60,
    ) -> Dict:
        """Upload a base64-encoded PNG to a GCS bucket and return a signed URL.

        Args:
            png_base64:         The base64-encoded PNG string (no data URI prefix).
            bucket_name:        Target GCS bucket name (must already exist).
            blob_name:          Object path inside the bucket. Auto-generated (UUID)
                                if not provided.
            expiration_minutes: How long the signed URL is valid (default 60 min).

        Returns a dict with:
            - 'gcs_uri'    : gs://bucket/blob path
            - 'signed_url' : HTTPS signed URL valid for `expiration_minutes`
            - 'markdown'   : ready-to-embed markdown image string

        Requirements:
            The GCS bucket must exist and the authenticated principal must have
            roles/storage.objectCreator + roles/storage.objectViewer.
            Signed URLs are generated using the 'signBlob' IAM API endpoint,
            which works with Application Default Credentials when the principal
            has roles/iam.serviceAccountTokenCreator on itself.
            If signing fails, the method falls back to a public URL
            (requires fine-grained ACL on the bucket).
        """
        # Strip data URI prefix if the LLM accidentally passes the full data_uri
        if "," in png_base64:
            png_base64 = png_base64.split(",", 1)[1].strip()
        # Add padding to avoid binascii.Error: Incorrect padding
        png_bytes = base64.b64decode(png_base64 + "==")

        if blob_name is None:
            blob_name = f"census_charts/{uuid.uuid4().hex}.png"

        ## initialize a gcs storage client
        client = storage.Client()
        ## initialize a gcs bucket object
        bucket = client.bucket(bucket_name)
        ## initialize a gcs blob object
        blob = bucket.blob(blob_name)
        ## call the function upload_from_string to upload a image which is represented by string
        blob.upload_from_string(png_bytes, content_type="image/png")

        gcs_uri = f"gs://{bucket_name}/{blob_name}"

        try:
            # generate_signed_url works with ADC when the service account has
            # iam.serviceAccounts.signBlob permission on itself.
            ### A signed URL for gcs object: A temporary, cryptographically signed link that gives someone time-limited access to a private object stored in Google Cloud Storage (GCS) — without making the object public.
            ## a temporary, cryptographically signed link that gives someone limited-time access to a private object on gcs without make it public.
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(minutes=expiration_minutes),
                method="GET",
            )
            url = signed_url
        except Exception:
            # Fallback to an empty url
            url = ""

        markdown = f"![Census Chart]({url})"

        return {
            "gcs_uri": gcs_uri,
            "url": url,
            "markdown": markdown,
            "blob_name": blob_name,
            "expiration_minutes": expiration_minutes,
        }
