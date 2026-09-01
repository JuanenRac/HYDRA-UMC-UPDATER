// =============================================================================
// HYDRA-UMC-UPDATER - Qt Quick visual desktop shell: Main.qml
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
// A real QML control surface over qt_gui.py's manifest/update bridge.  No
// project row, metric or operation result is hard-coded here: the Python
// backend supplies actual discovery and update data to this presentation.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.VectorImage

ApplicationWindow {
    id: window
    width: 1500
    height: 900
    minimumWidth: 1100
    minimumHeight: 680
    visible: true
    title: "HYDRA-UMC Updater"
    color: "#07111e"

    property string languageTick: backend.language
    property color canvasColor: "#07111e"
    property color panel: "#101d30"
    property color panelAlt: "#14253b"
    property color border: "#294965"
    property color textPrimary: "#edf7ff"
    property color textMuted: "#91a8bd"
    property color cyan: "#38d4e6"
    property color blue: "#397dff"
    property color green: "#43db9b"
    property color amber: "#f3ba55"
    property color red: "#ee6b80"

    function ui(key) {
        // Keeping this dependency makes all bound labels refresh when the
        // language changes, without a duplicated QML translation catalogue.
        var ignored = languageTick
        return backend.text(key)
    }

    function stateColor(stateKey) {
        if (stateKey === "state_outdated") return red
        if (stateKey === "state_up_to_date") return green
        if (stateKey === "state_not_installed") return textMuted
        if (stateKey === "state_ahead") return amber
        return cyan
    }

    function checkpointColor(state) {
        if (state === "done") return green
        if (state === "active") return cyan
        if (state === "failed") return red
        if (state === "skipped") return textMuted
        return border
    }

    component LabelText: Text {
        color: window.textPrimary
        // Bahnschrift gives Windows the intended angular/technical character;
        // Qt falls back cleanly to the system sans family on Linux/CM5.
        font.family: "Bahnschrift"
        font.pixelSize: 12
        renderType: Text.QtRendering
    }

    component SectionPanel: Rectangle {
        color: window.panel
        radius: 16
        border.width: 1
        border.color: window.border
    }

    component MetricCard: Rectangle {
        id: metric
        required property string caption
        required property string value
        required property color accent
        color: window.panelAlt
        radius: 11
        height: 72
        border.width: 1
        border.color: Qt.rgba(accent.r, accent.g, accent.b, 0.35)
        Row {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10
            Rectangle { width: 4; height: parent.height; radius: 2; color: metric.accent }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                LabelText { text: metric.value; color: metric.accent; font.pixelSize: 22; font.bold: true }
                LabelText { text: metric.caption; color: window.textMuted; font.pixelSize: 11 }
            }
        }
    }

    // Qt Controls use the platform style by default, which can mean dark
    // text over our dark background. These components own every colour and
    // font used by interactive controls so the visual language is stable on
    // Windows, Linux and a future CM5 desktop session.
    component GameButton: Button {
        id: gameButton
        property color accent: window.blue
        implicitHeight: 42
        hoverEnabled: true
        font.family: "Bahnschrift"
        font.pixelSize: 12
        font.bold: true
        contentItem: Text {
            text: gameButton.text
            color: gameButton.enabled ? "#f5fbff" : "#6d8294"
            font: gameButton.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 10
            border.width: 1
            border.color: gameButton.enabled ? Qt.lighter(gameButton.accent, gameButton.hovered ? 1.28 : 1.08) : "#25384b"
            color: !gameButton.enabled ? "#122031" : (gameButton.down ? Qt.darker(gameButton.accent, 1.38) : (gameButton.hovered ? Qt.lighter(gameButton.accent, 1.14) : gameButton.accent))
            Behavior on color { ColorAnimation { duration: 130 } }
            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 1; radius: 1; color: gameButton.enabled ? "#9eeeff" : "#34495c"; opacity: 0.55 }
        }
    }

    // A real Version/Author/Email/License info row, matching
    // HYDRA-UMC-STUDIO's own About.tsx InfoRow.
    component AboutInfoRow: Rectangle {
        property string label: ""
        property string value: ""
        property color valueColor: window.textPrimary
        Layout.fillWidth: true
        implicitHeight: 34
        radius: 8
        color: "#07111e"
        border.width: 1
        border.color: window.border
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            LabelText { text: label.toUpperCase(); color: window.textMuted; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1 }
            Item { Layout.fillWidth: true }
            LabelText { text: value; color: valueColor; font.pixelSize: 11 }
        }
    }

    component GameCombo: ComboBox {
        id: gameCombo
        implicitHeight: 40
        font.family: "Bahnschrift"
        font.pixelSize: 12
        contentItem: Text {
            leftPadding: 13
            rightPadding: 34
            text: gameCombo.displayText
            color: "#edf7ff"
            font: gameCombo.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        indicator: Text {
            x: gameCombo.width - width - 13
            y: (gameCombo.height - height) / 2 - 1
            text: "⌄"
            color: window.cyan
            font.family: "Bahnschrift"
            font.pixelSize: 20
        }
        background: Rectangle {
            radius: 10
            color: gameCombo.pressed ? "#1a3954" : (gameCombo.hovered ? "#19334d" : "#12263a")
            border.width: 1
            border.color: gameCombo.hovered ? "#3dcce0" : "#315773"
            Behavior on color { ColorAnimation { duration: 120 } }
        }
        delegate: ItemDelegate {
            width: gameCombo.width
            height: 39
            contentItem: Text {
                text: modelData.label || modelData
                color: "#edf7ff"
                font.family: "Bahnschrift"
                font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
                leftPadding: 13
            }
            background: Rectangle { color: highlighted ? "#23516e" : "#10243a" }
        }
        popup: Popup {
            y: gameCombo.height + 5
            width: gameCombo.width
            implicitHeight: contentItem.implicitHeight
            padding: 1
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: gameCombo.popup.visible ? gameCombo.delegateModel : null
                currentIndex: gameCombo.highlightedIndex
            }
            background: Rectangle { radius: 10; color: "#10243a"; border.width: 1; border.color: "#3dcce0" }
        }
    }

    component GameCheck: CheckBox {
        id: gameCheck
        implicitHeight: 30
        hoverEnabled: true
        indicator: Rectangle {
            implicitWidth: 19
            implicitHeight: 19
            x: gameCheck.leftPadding
            y: parent.height / 2 - height / 2
            radius: 5
            color: gameCheck.checked ? window.cyan : "#10243a"
            border.width: 1
            border.color: gameCheck.hovered ? "#67e5f0" : "#42647c"
            Text { anchors.centerIn: parent; text: gameCheck.checked ? "✓" : ""; color: "#07111e"; font.pixelSize: 15; font.bold: true }
        }
        contentItem: Text {
            text: gameCheck.text
            color: gameCheck.enabled ? window.textMuted : "#5d7184"
            font.family: "Bahnschrift"
            font.pixelSize: 11
            leftPadding: gameCheck.indicator.width + 10
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }

    FolderDialog {
        id: workspaceDialog
        title: ui("workspace_caption")
        onAccepted: backend.setWorkspaceUrl(selectedFolder.toString())
    }

    Dialog {
        id: confirmDialog
        modal: true
        anchors.centerIn: parent
        width: 430
        padding: 22
        property string action: "update"
        property bool batch: false
        background: Rectangle { color: window.panel; radius: 16; border.color: window.border; border.width: 1 }
        contentItem: ColumnLayout {
            spacing: 14
            LabelText { text: confirmDialog.batch ? ui("confirm_batch_title") : ui("confirm_action_title"); font.pixelSize: 18; font.bold: true }
            LabelText {
                text: {
                    if (!confirmDialog.batch) return ui("confirm_action_body").replace("{project}", backend.selectedProject)
                    var count = confirmDialog.action === "install" ? backend.missingCount : backend.updateCount
                    var key = confirmDialog.action === "install" ? "confirm_batch_install_body" : "confirm_batch_update_body"
                    return ui(key).replace("{count}", String(count))
                }
                color: window.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                GameButton { text: ui("confirm_cancel_button"); accent: "#27445d"; onClicked: confirmDialog.close() }
                GameButton {
                    text: confirmDialog.action === "install" ? ui("install_button") : ui("update_button")
                    onClicked: {
                        if (confirmDialog.batch) backend.performBatch(confirmDialog.action, skipBuild.checked)
                        else backend.performSelected(confirmDialog.action, skipBuild.checked)
                        confirmDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: aboutDialog
        modal: true
        anchors.centerIn: parent
        width: 440
        padding: 24
        background: Rectangle { color: window.panel; radius: 16; border.color: window.border; border.width: 1 }
        contentItem: ColumnLayout {
            spacing: 8

            // Real animated mark, same source and renderer as the main
            // header above - not a placeholder "H" box.
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Rectangle {
                    Layout.preferredWidth: 88; Layout.preferredHeight: 88; radius: 20
                    color: "#0e3045"; border.width: 1; border.color: "#2d7695"
                    VectorImage {
                        anchors.fill: parent; anchors.margins: 10
                        source: "../../../images/HYDRA_UMC_ICON.svg"
                        preferredRendererType: VectorImage.CurveRenderer
                        animations.loops: Animation.Infinite
                        animations.paused: false
                    }
                }
                Item { Layout.fillWidth: true }
            }

            LabelText {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: "HYDRA<font color=\"" + window.green + "\">-UM</font><font color=\"" + window.red + "\">C</font> <font color=\"" + window.cyan + "\">UPDATER</font>"
                textFormat: Text.RichText
                font.pixelSize: 20
                font.bold: true
                font.letterSpacing: 1
            }
            LabelText {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: ui("about_tagline")
                color: window.cyan
                font.pixelSize: 12
                font.bold: true
            }
            LabelText {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: ui("about_description")
                color: window.textMuted
                font.pixelSize: 11
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.topMargin: 6
                spacing: 4
                AboutInfoRow { label: ui("about_version_label"); value: backend.appVersion }
                AboutInfoRow { label: ui("about_author_label"); value: "JuanenRac (Electro Hobby 3D)" }
                AboutInfoRow {
                    label: ui("about_email_label")
                    valueColor: window.cyan
                    value: "electrohobby3d@gmail.com"
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Qt.openUrlExternally("mailto:electrohobby3d@gmail.com") }
                }
                AboutInfoRow { label: ui("about_license_label"); value: ui("about_license") }
            }

            RowLayout { Layout.fillWidth: true; Layout.topMargin: 8
                GameButton { text: ui("open_github_button"); accent: "#264966"; onClicked: Qt.openUrlExternally("https://github.com/JuanenRac/HYDRA-UMC-UPDATER") }
                Item { Layout.fillWidth: true }
                GameButton { text: ui("about_close_button"); accent: window.cyan; onClicked: aboutDialog.close() }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0a1a2b" }
            GradientStop { position: 0.46; color: "#07111e" }
            GradientStop { position: 1.0; color: "#06101a" }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 28
        anchors.rightMargin: 28
        anchors.topMargin: 22
        anchors.bottomMargin: 18
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 78
            spacing: 16
            Rectangle {
                width: 54; height: 54; radius: 16
                color: "#0e3045"; border.width: 1; border.color: "#2d7695"
                // Image rasterizes SVG into one image for this surface.
                // VectorImage preserves the official SVG's supported SMIL
                // transform animation, so the mark remains alive instead
                // of becoming a static logo in the Updater command header.
                VectorImage {
                    anchors.fill: parent
                    anchors.margins: 5
                    source: "../../../images/HYDRA_UMC_ICON.svg"
                    preferredRendererType: VectorImage.CurveRenderer
                    animations.loops: Animation.Infinite
                    animations.paused: false
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                LabelText { text: "HYDRA-UMC"; color: window.cyan; font.pixelSize: 13; font.bold: true; font.letterSpacing: 1.2 }
                LabelText { text: "UPDATER"; font.pixelSize: 27; font.bold: true; font.letterSpacing: 1.1 }
                LabelText { text: ui("ui_subtitle"); color: window.textMuted; font.pixelSize: 13 }
            }
            Rectangle {
                color: "#10283a"; radius: 13; border.color: "#21516a"; border.width: 1
                Layout.preferredWidth: 225; Layout.preferredHeight: 48
                Row { anchors.centerIn: parent; spacing: 9
                    Rectangle { width: 9; height: 9; radius: 5; color: backend.busy ? window.amber : window.green
                        SequentialAnimation on opacity {
                            running: backend.busy
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.32; duration: 620 }
                            NumberAnimation { to: 1; duration: 620 }
                        }
                    }
                    LabelText { text: backend.busy ? ui("status_busy") : ui("status_online"); color: window.textMuted; font.pixelSize: 11; font.bold: true }
                }
            }
            GameButton { text: ui("menu_about"); accent: "#264966"; Layout.alignment: Qt.AlignRight; onClicked: aboutDialog.open() }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 45
            spacing: 10
            LabelText { text: ui("show_label"); color: window.textMuted; font.pixelSize: 12 }
            GameCombo {
                id: deployCombo
                Layout.preferredWidth: 230
                model: backend.deployOptions
                textRole: "label"
                onActivated: backend.setDeploy(backend.deployOptions[currentIndex].key)
            }
            GameCheck { id: offlineCheck; text: ui("offline_checkbox") }
            Item { Layout.fillWidth: true }
            LabelText { text: ui("lang_label"); color: window.textMuted; font.pixelSize: 12 }
            GameCombo {
                id: languageCombo
                Layout.preferredWidth: 145
                model: [
                    { code: "en", label: "English" }, { code: "es", label: "Español" },
                    { code: "fr", label: "Français" }, { code: "it", label: "Italiano" },
                    { code: "de", label: "Deutsch" }, { code: "zh", label: "简体中文" },
                    { code: "ja", label: "日本語" }
                ]
                textRole: "label"
                Component.onCompleted: {
                    for (var i = 0; i < model.length; ++i) if (model[i].code === backend.language) currentIndex = i
                }
                onActivated: backend.setLanguage(model[currentIndex].code)
            }
            GameButton { text: ui("refresh_button"); enabled: !backend.busy; accent: window.cyan; onClicked: backend.refresh(offlineCheck.checked) }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            SectionPanel {
                Layout.preferredWidth: 275
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 12
                    LabelText { text: ui("local_ecosystem_title"); font.pixelSize: 18; font.bold: true }
                    LabelText { text: ui("workspace_caption"); color: window.textMuted; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1 }
                    LabelText { text: backend.workspaceRoot; color: window.textPrimary; font.pixelSize: 11; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                    GameButton { text: ui("browse_button"); Layout.fillWidth: true; accent: "#265c89"; onClicked: workspaceDialog.open() }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border }
                    MetricCard { Layout.fillWidth: true; caption: ui("metric_detected"); value: String(backend.discoveredCount); accent: window.cyan }
                    MetricCard { Layout.fillWidth: true; caption: ui("metric_installed"); value: String(backend.installedCount); accent: window.green }
                    MetricCard { Layout.fillWidth: true; caption: ui("metric_updates"); value: String(backend.updateCount); accent: window.amber }
                    Item { Layout.fillHeight: true }
                    LabelText { text: ui("local_footer"); color: window.textMuted; wrapMode: Text.WordWrap; font.pixelSize: 11; Layout.fillWidth: true }
                }
            }

            SectionPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 10
                    RowLayout { Layout.fillWidth: true
                        LabelText { text: ui("registry_title"); font.pixelSize: 18; font.bold: true; Layout.fillWidth: true }
                        LabelText { text: String(backend.discoveredCount) + " " + ui("metric_detected"); color: window.cyan; font.pixelSize: 11 }
                    }
                    LabelText { text: ui("registry_hint"); color: window.textMuted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 31; color: "#172a40"; radius: 7
                        RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 8
                            Repeater { model: [ui("col_project"), ui("col_maturity"), ui("col_stack"), ui("col_local"), ui("col_github"), ui("col_state")]
                                delegate: LabelText { required property string modelData; text: modelData; color: window.textMuted; font.pixelSize: 10; font.bold: true; Layout.fillWidth: modelData === ui("col_project"); Layout.preferredWidth: modelData === ui("col_project") ? 210 : 83 }
                            }
                        }
                    }
                    ListView {
                        id: projectList
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 4
                        model: backend.projects
                        ScrollBar.vertical: ScrollBar { }
                        delegate: Rectangle {
                            required property var modelData
                            property var project: modelData
                            width: projectList.width; height: 52; radius: 8
                            color: project.name === backend.selectedProject ? "#1a4967" : (rowArea.containsMouse ? "#172c43" : "#112238")
                            border.width: project.name === backend.selectedProject ? 1 : 0
                            border.color: "#3ac9dc"
                            Behavior on color { ColorAnimation { duration: 130 } }
                            MouseArea { id: rowArea; anchors.fill: parent; hoverEnabled: true; onClicked: backend.selectProject(project.name) }
                            RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 8
                                LabelText { text: (project.isChild ? "↳  " : "◆  ") + project.name; color: project.isChild ? window.textMuted : window.textPrimary; font.pixelSize: 11; Layout.fillWidth: true; Layout.preferredWidth: 210; elide: Text.ElideRight }
                                LabelText { text: project.maturity; color: window.textMuted; font.pixelSize: 10; Layout.preferredWidth: 83; horizontalAlignment: Text.AlignHCenter }
                                LabelText { text: project.stack; color: window.textMuted; font.pixelSize: 10; Layout.preferredWidth: 83; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight }
                                LabelText { text: project.local; color: window.textMuted; font.pixelSize: 10; Layout.preferredWidth: 83; horizontalAlignment: Text.AlignHCenter }
                                LabelText { text: project.github; color: window.textMuted; font.pixelSize: 10; Layout.preferredWidth: 83; horizontalAlignment: Text.AlignHCenter }
                                LabelText { text: project.state; color: window.stateColor(project.stateKey); font.pixelSize: 10; font.bold: true; Layout.preferredWidth: 100; elide: Text.ElideRight }
                            }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 72; radius: 9; color: window.panelAlt
                        LabelText { anchors.fill: parent; anchors.margins: 11; text: backend.selectedNotes(); color: window.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap; elide: Text.ElideRight }
                    }
                }
            }

            SectionPanel {
                Layout.preferredWidth: 305
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 11
                    LabelText { text: ui("safe_update_title"); font.pixelSize: 18; font.bold: true }
                    LabelText { text: ui("safe_update_hint"); color: window.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    ColumnLayout {
                        visible: !backend.operationVisible
                        Layout.fillWidth: true
                        Layout.preferredHeight: visible ? implicitHeight : 0
                        spacing: 9
                        LabelText { text: ui("selected_project_caption"); color: window.textMuted; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1 }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 55; radius: 10; color: window.panelAlt; border.width: 1; border.color: window.border
                            LabelText { anchors.fill: parent; anchors.margins: 12; text: backend.selectedProject; font.pixelSize: 12; font.bold: true; wrapMode: Text.WrapAnywhere; verticalAlignment: Text.AlignVCenter }
                        }
                        GameButton { text: ui("install_button"); enabled: !backend.busy && backend.canInstall; Layout.fillWidth: true; accent: window.blue; onClicked: { confirmDialog.batch = false; confirmDialog.action = "install"; confirmDialog.open() } }
                        GameButton { text: ui("update_button"); enabled: !backend.busy && backend.canUpdate; Layout.fillWidth: true; accent: window.green; onClicked: { confirmDialog.batch = false; confirmDialog.action = "update"; confirmDialog.open() } }
                        GameCheck { id: skipBuild; text: ui("skip_build_checkbox"); Layout.fillWidth: true }
                        GameButton { text: ui("open_github_button"); enabled: backend.selectedProject !== ui("selected_project_none"); Layout.fillWidth: true; accent: "#264966"; onClicked: backend.openSelectedGithub() }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border }
                        LabelText { text: ui("batch_actions_title"); color: window.textMuted; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1 }
                        GameButton { text: ui("install_all_button").replace("{count}", String(backend.missingCount)); enabled: !backend.busy && backend.canInstallAll; Layout.fillWidth: true; accent: "#265c89"; onClicked: { confirmDialog.batch = true; confirmDialog.action = "install"; confirmDialog.open() } }
                        GameButton { text: ui("update_all_button").replace("{count}", String(backend.updateCount)); enabled: !backend.busy && backend.canUpdateAll; Layout.fillWidth: true; accent: "#3a8f68"; onClicked: { confirmDialog.batch = true; confirmDialog.action = "update"; confirmDialog.open() } }
                    }
                    ColumnLayout {
                        visible: backend.operationVisible
                        Layout.fillWidth: true
                        Layout.preferredHeight: visible ? implicitHeight : 0
                        spacing: 9
                        LabelText { text: backend.operationHeading; font.pixelSize: 12; font.bold: true; font.letterSpacing: 1; Layout.fillWidth: true; elide: Text.ElideRight }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 10; radius: 5; color: "#081623"; border.width: 1; border.color: "#1d4056"
                            Rectangle {
                                width: parent.width * backend.operationProgress / 100
                                height: parent.height; radius: 5; color: backend.busy ? window.cyan : (backend.operationProgress === 100 ? window.green : "#315773")
                                Behavior on width { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
                            }
                        }
                        LabelText { text: String(backend.operationProgress) + "%  " + backend.operationDetail; color: window.textMuted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Repeater {
                            model: backend.operationSteps
                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true; spacing: 8
                                Rectangle { Layout.preferredWidth: 15; Layout.preferredHeight: 15; radius: 8; color: window.checkpointColor(modelData.state); border.width: 1; border.color: Qt.lighter(window.checkpointColor(modelData.state), 1.2)
                                    LabelText { anchors.centerIn: parent; text: modelData.state === "done" ? "✓" : (modelData.state === "failed" ? "!" : (modelData.state === "active" ? "›" : "")); color: "#07111e"; font.pixelSize: 11; font.bold: true }
                                }
                                LabelText { text: modelData.label; color: modelData.state === "pending" ? window.textMuted : window.textPrimary; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                            }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border }
                    LabelText { text: ui("safety_title"); font.pixelSize: 12; font.bold: true; font.letterSpacing: 1 }
                    LabelText { text: ui("safety_summary"); color: window.textMuted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    LabelText { text: ui("activity_log_title"); font.pixelSize: 12; font.bold: true; font.letterSpacing: 1 }
                    Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; color: "#081623"; radius: 9; border.width: 1; border.color: "#1d4056"
                        ListView { anchors.fill: parent; anchors.margins: 10; model: backend.activity; clip: true; spacing: 6
                            delegate: LabelText { required property string modelData; text: "› " + modelData; color: "#9adce3"; font.family: "Cascadia Mono"; font.pixelSize: 10; width: parent.width; wrapMode: Text.WordWrap }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 35; radius: 8; color: "#091827"; border.width: 1; border.color: "#17354a"
            RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12
                LabelText { text: ui("status_caption"); color: window.cyan; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1 }
                LabelText { text: backend.status; color: window.textMuted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                BusyIndicator { running: backend.busy; visible: running; Layout.preferredWidth: 22; Layout.preferredHeight: 22 }
            }
        }
    }
}
