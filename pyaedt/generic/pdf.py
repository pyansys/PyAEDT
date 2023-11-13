import os
import warnings

from pyaedt import __version__
from pyaedt import pyaedt_path
from pyaedt import settings
from pyaedt.generic.clr_module import List
from pyaedt.generic.clr_module import _clr
from pyaedt.generic.clr_module import is_clr

if not settings.use_grpc_edb_api:
    from pyedb.legacy.edb_core.general import convert_py_list_to_net_list
else:
    print("gRPC Not yet available.")


try:
    _clr.AddReference("AnsysReport")
    from AnsysReport import CreatePdfReport
    from AnsysReport import ReportSpec
except ImportError:
    msg = "pythonnet or dotnetcore not installed. Pyaedt will work only in client mode."
    warnings.warn(msg)


class AnsysReport:
    """Generate a pdf report."""

    def __init__(self, version="2023R1", design_name="design1", project_name="AnsysProject", tempplate_json_file=None):
        assert is_clr, ".Net Core 3.1 is needed to run AnsysReport."
        self.report_specs = ReportSpec()
        self.report_specs.AnsysVersion = version
        self.report_specs.DesignName = design_name
        self.report_specs.ProjectName = project_name
        self.report_specs.PyAEDTVersion = __version__
        if tempplate_json_file:
            self.report_specs.TemplateName = tempplate_json_file

    def create(self, add_header=True, add_first_page=True):
        """Create a new report using ``report_specs`` properties.

        Parameters
        ----------
        add_header :bool, optional
            Whether to add pdf header or not. Default is ``True``.
        add_first_page :bool, optional
            Whether to add first page with title  or not. Default is ``True``.

        Returns
        -------
        :class:`AnsysReport`
        """
        self.report = CreatePdfReport(os.path.join(pyaedt_path, "dlls", "PDFReport"))
        self.report.Specs = self.report_specs
        if add_header:
            self.report.AddAnsysHeader(-1)
        if add_first_page:
            self.report.AddFirstPage()
        return self.report

    @property
    def template_name(self):
        """Get/set the template to use.
        It can be a full json path or a string of a json contained in ``"Images"`` folder.


        Returns
        -------
        str
        """
        return self.report_specs.TemplateName

    @template_name.setter
    def template_name(self, value):
        self.report_specs.TemplateName = value

    @property
    def design_name(self):
        """Get/set the design name for report header.

        Returns
        -------
        str
        """
        return self.report_specs.DesignName

    @design_name.setter
    def design_name(self, value):
        self.report_specs.DesignName = value

    @property
    def project_name(self):
        """Get/set the project name for report header.

        Returns
        -------
        str
        """
        return self.report_specs.ProjectName

    @project_name.setter
    def project_name(self, value):
        self.report_specs.ProjectName = value

    @property
    def aedt_version(self):
        """Get/set the aedt version for report header.

        Returns
        -------
        str
        """
        return self.report_specs.AnsysVersion

    @aedt_version.setter
    def aedt_version(self, value):
        self.report_specs.AnsysVersion = value

    def add_section(self, portrait=True):
        """Add a new section to Pdf.

        Parameters
        ----------
        portrait : bool, optional
            Section orientation. Default ``True`` for portrait.

        Returns
        -------
        int,
            Section id.
        """
        orientation = "P" if portrait else "L"
        return self.report.CreateNewSection(orientation)

    def add_chapter(self, chapter_name, section_id=0):
        """Add a new chapter.

        Parameters
        ----------
        chapter_name : str
            Chapter name.
        section_id : int, optional
            Section on which add the chapter. Default is 0 which use current section.
        """
        self.report.AddChapter(chapter_name, section_id)

    def add_sub_chapter(self, chapter_name, section_id=0):
        """Add a new sub-chapter.

        Parameters
        ----------
        chapter_name : str
            Chapter name.
        section_id : int, optional
            Section on which add the subchapter. Default is 0 which use current section.
        """
        return self.report.AddSubChapter(chapter_name, section_id)

    def add_image(self, path, caption="", width=10, section_id=0):
        """Add a new image.

        Parameters
        ----------
        path : str
            Image path.
        caption : str, optional
            Image caption.
        width : int, optional
            Image width in centimeters.
        section_id : int, optional
            Section on which add the chapter. Default is 0 which use current section.
        """
        return self.report.AddImageWithCaption(path, caption, width, section_id)

    def add_caption(self, content, section_id=0):
        """Add a new caption.

        Parameters
        ----------
        content : str
            Caption name.
        section_id : int, optional
            Section on which add the caption. Default is 0 which use current section.
        """
        return self.report.AddCaption(content, section_id)

    def add_empty_line(self, num_lines=1, section_id=0):
        """Add a new empty line.

        Parameters
        ----------
        num_lines : int, optional
            Number of lines to add.
        section_id : int, optional
            Section on which add the lines. Default is 0 which use current section.
        """
        return self.report.AddEmptyLines(num_lines, section_id)

    def add_page_break(self, section_id=0):
        """Add a new page break line.

        Parameters
        ----------
        section_id : int, optional
            Section on which add the lines. Default is 0 which use current section.
        """
        return self.report.AddPageBreak(section_id)

    def add_table(
        self,
        title,
        content,
        is_centered=True,
        transposed=True,
        bold_first_row=True,
        bold_first_column=True,
        section_id=0,
    ):
        """Add a new table from a list of data.
        Data shall be a list of list where every line is either a row or a column.

        Parameters
        ----------
        title : str
            Table title.
        content : list of list
            Table content.
        is_centered : bool, optional
            Whether if table is centered or not. Default is ``True``.
        transposed : bool, optional
            Whether if data are transposed or not. Default is ``True``.
        bold_first_row : bool, optional
            Whether if first row will be bolded or not. Default is ``True``.
        bold_first_column : bool, optional
            Whether if first column will be bolded or not. Default is ``True``.
        section_id : int, optional
            Section on which add the lines. Default is 0 which use current section.
        """
        content_sharp = List[type(List[str]())]()
        for el in content:
            content_sharp.Add(convert_py_list_to_net_list([str(i) for i in el]))
        return self.report.AddTableFromList(
            title, content_sharp, is_centered, transposed, bold_first_row, bold_first_column, section_id
        )

    def add_text(self, content, bold=False, italic=False, section_id=0):
        """Add a new text.

        Parameters
        ----------
        content : str
            Text content.
        bold : bool, optional
            Whether if text is bold or not. Default is ``True``.
        italic : bool, optional
            Whether if text is italic or not. Default is ``True``.
        section_id : int, optional
            Section on which add the caption. Default is 0 which use current section.
        """
        self.report.AddText(content, bold, italic, section_id)

    def add_toc(self):
        """Add Table of content."""
        self.report.AddTableOfContent()

    def save_pdf(self, file_path, file_name=None, open=False):
        """Save pdf.

        Parameters
        ----------
        file_path : str
            Pdf path.
        file_name : str, optional
            File name.
        open : bool, optional
            Whether if open the pdf at the end or not.
        """
        if open:
            if not file_name:
                file_name = self.report_specs.ProjectName + "_" + self.report_specs.Revision + ".pdf"
            self.report.SaveAndOpenPDF(os.path.join(file_path, file_name))
            return os.path.join(file_path, file_name)
        else:
            return self.report.SavePDF(file_path, file_name)

    def add_chart(self, x_values, y_values, x_caption, y_caption, title, section_id=0):
        """Add a chart to the report.

        Parameters
        ----------
        x_values : list
            list of float x values.
        y_values : list
            List of float y values.
        x_caption : str
            X axis caption.
        y_caption : str
            Y axis caption.
        title : str
            Chart title.
        section_id : int, optional
            Section on which add the caption. Default is 0 which use current section.
        """
        self.report.CreateCustomChart(
            convert_py_list_to_net_list(x_values, float),
            convert_py_list_to_net_list(y_values, float),
            x_caption,
            y_caption,
            title,
            section_id,
        )
