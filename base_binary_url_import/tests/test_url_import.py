# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
import base64
import io
from contextlib import contextmanager

import responses

from odoo.modules.module import get_resource_path
from odoo.tests.common import Form, TransactionCase


class TestUrlImport(TransactionCase):
    def setUp(self, *args, **kwargs):
        super().setUp()
        self.demo_record_1 = self.env["ir.attachment"].create(
            {"name": "Demo1", "type": "binary"}
        )
        self.demo_record_2 = self.env["ir.attachment"].create(
            {"name": "Demo2", "type": "binary"}
        )
        self.demo_url1 = "https://www.example.com/test.txt"
        self.demo_url2 = "https://www.example.com/test.pdf"
        self.copy_paste_text = "%s,%s\n%s,%s" % (
            self.demo_record_1.id,
            self.demo_url1,
            self.demo_record_2.id,
            self.demo_url2,
        )
        self.ir_attachment_ir_model = self.env["ir.model"].search(
            [("model", "=", "ir.attachment")]
        )
        self.ir_attachment_file_ir_model_fields = self.env["ir.model.fields"].search(
            [("model_id", "=", self.ir_attachment_ir_model.id), ("name", "=", "datas")]
        )
        self.ir_attachment_filename_ir_model_fields = self.env[
            "ir.model.fields"
        ].search(
            [
                ("model_id", "=", self.ir_attachment_ir_model.id),
                ("name", "=", "name"),
            ]
        )

    @contextmanager
    def yield_wizard_form(self):
        with Form(self.env["base.binary.url.import"]) as wizard_form:
            wizard_form.target_model_id = self.ir_attachment_ir_model
            wizard_form.target_binary_field_id = self.ir_attachment_file_ir_model_fields
            yield wizard_form

    @responses.activate
    def test_wizard_import(self):
        txt_binary = io.BytesIO()
        txt_file_path = get_resource_path(
            "base_binary_url_import", "tests", "files", "test.txt"
        )
        with open(txt_file_path, "rb") as txt_file:
            txt_binary.write(txt_file.read())
        responses.add(
            responses.GET,
            self.demo_url1,
            body=txt_binary.getvalue(),
            status=200,
            content_type="text/plain",
            # stream=True,
        )
        pdf_binary = io.BytesIO()
        pdf_file_path = get_resource_path(
            "base_binary_url_import", "tests", "files", "test.pdf"
        )
        with open(pdf_file_path, "rb") as pdf_file:
            pdf_binary.write(pdf_file.read())
        responses.add(
            responses.GET,
            self.demo_url2,
            body=pdf_binary.getvalue(),
            status=200,
            content_type="application/pdf",
            # stream=True,
        )
        wizard_form = Form(self.env["base.binary.url.import"])
        wizard_form.target_model_id = self.ir_attachment_ir_model
        wizard_form.target_binary_field_id = self.ir_attachment_file_ir_model_fields
        wizard_form.target_binary_filename_field_id = (
            self.ir_attachment_filename_ir_model_fields
        )
        with wizard_form.line_ids.new() as line_form:
            line_form.binary_url_to_import = self.copy_paste_text
        wizard = wizard_form.save()
        self.assertFalse(self.demo_record_1.datas)
        self.assertEqual(self.demo_record_1.name, "Demo1")
        self.assertFalse(self.demo_record_2.datas)
        self.assertEqual(self.demo_record_2.name, "Demo2")
        wizard.action_import_lines()
        self.assertEqual(
            base64.b64decode(self.demo_record_1.datas), txt_binary.getvalue()
        )
        self.assertEqual(self.demo_record_1.name, "test.txt")
        self.assertEqual(
            base64.b64decode(self.demo_record_2.datas), pdf_binary.getvalue()
        )
        self.assertEqual(self.demo_record_2.name, "test.pdf")
